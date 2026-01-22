from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import uuid
import shutil

from app.config import get_settings
from app.config import get_settings
from app.services.ingestion_service import get_ingestion_service
from app.services.vector_store import get_vector_store
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


class UploadResponse(BaseModel):
    """Response model for file upload."""
    success: bool
    document_id: str
    filename: str
    message: str
    chunks_created: int
    page_count: Optional[int] = None



class DocumentInfo(BaseModel):
    """Document information model."""
    document_id: str
    filename: str
    chunk_count: int


class UrlUploadRequest(BaseModel):
    """Request model for URL upload."""
    url: str



@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a PDF document using IngestionService.
    """
    settings = get_settings()
    service = get_ingestion_service()
    
    # Check file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    max_size = settings.max_file_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_file_size_mb}MB"
        )
    
    # Save file temporarily
    upload_dir = settings.upload_dir
    os.makedirs(upload_dir, exist_ok=True)
    
    safe_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved: {file_path}")
        
        # Use IngestionService to process the file
        result = service.ingest_file(file_path)
        
        if not result.success:
            raise Exception(result.error)
            
        return UploadResponse(
            success=True,
            document_id=result.document_id,
            filename=file.filename,
            message="Document uploaded and indexed successfully",
            chunks_created=result.chunk_count,
            page_count=None # IngestionResult doesn't expose page count directly yet
        )
        
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        # Clean up file on error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )


@router.post("/upload-url", response_model=UploadResponse)
async def upload_url(request: UrlUploadRequest):
    """
    Upload and process a document from a URL.
    Automatically detects GitHub repositories and uses appropriate adapter.
    """
    service = get_ingestion_service()
    
    try:
        # Auto-detect if it's a GitHub URL
        is_github = 'github.com' in request.url.lower()
        
        if is_github:
            # Use GitHub adapter - returns list of results
            results = service.ingest_github(request.url)
            
            # Aggregate results for GitHub repos (multiple files)
            if not results or not any(r.success for r in results):
                raise Exception("Failed to ingest GitHub repository")
            
            total_chunks = sum(r.chunk_count for r in results if r.success)
            successful_count = sum(1 for r in results if r.success)
            
            return UploadResponse(
                success=True,
                document_id=results[0].document_id if results else "",
                filename=f"GitHub: {request.url.split('/')[-1]} ({successful_count} files)",
                message=f"GitHub repository processed: {successful_count} files indexed successfully",
                chunks_created=total_chunks,
                page_count=None
            )
        else:
            # Use regular URL adapter
            result = service.ingest_url(request.url)
            
            if not result.success:
                raise Exception(result.error)
                
            return UploadResponse(
                success=True,
                document_id=result.document_id,
                filename=result.source_name,
                message="URL content processed and indexed successfully",
                chunks_created=result.chunk_count,
                page_count=None
            )
        
    except Exception as e:
        logger.error(f"Error processing URL {request.url}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing URL: {str(e)}"
        )

@router.get("/documents")
async def list_documents():
    """List all uploaded documents."""
    settings = get_settings()
    upload_dir = settings.upload_dir
    
    if not os.path.exists(upload_dir):
        return {"documents": []}
    
    documents = []
    vector_store = get_vector_store()
    
    for filename in os.listdir(upload_dir):
        if filename.endswith('.pdf'):
            # Extract document ID from filename
            parts = filename.split('_', 1)
            if len(parts) == 2:
                doc_id = parts[0]
                original_name = parts[1]
                
                # Get chunk count from vector store
                chunks = vector_store.get_documents_by_id(doc_id)
                
                documents.append({
                    "document_id": doc_id,
                    "filename": original_name,
                    "chunk_count": len(chunks)
                })
    
    return {"documents": documents}


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and its embeddings."""
    settings = get_settings()
    
    # Delete from vector store
    vector_store = get_vector_store()
    deleted = vector_store.delete_document(document_id)
    
    # Delete file
    upload_dir = settings.upload_dir
    file_deleted = False
    
    if os.path.exists(upload_dir):
        for filename in os.listdir(upload_dir):
            if filename.startswith(document_id):
                file_path = os.path.join(upload_dir, filename)
                os.remove(file_path)
                file_deleted = True
                logger.info(f"Deleted file: {file_path}")
                break
    
    if deleted or file_deleted:
        return {"success": True, "message": "Document deleted"}
    else:
        raise HTTPException(status_code=404, detail="Document not found")
