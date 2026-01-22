from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import uuid
import shutil

from app.config import get_settings
from app.services.document_parser import DocumentParser
from app.services.chunker import DocumentChunker
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


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a PDF document.
    
    - Saves the file to upload directory
    - Parses PDF content
    - Chunks the content
    - Stores embeddings in vector database
    """
    settings = get_settings()
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, 
            detail="Only PDF files are supported"
        )
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    max_size = settings.max_file_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_file_size_mb}MB"
        )
    
    # Generate document ID
    document_id = str(uuid.uuid4())
    
    # Save file
    upload_dir = settings.upload_dir
    os.makedirs(upload_dir, exist_ok=True)
    
    safe_filename = f"{document_id}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved: {file_path}")
        
        # Parse document
        parser = DocumentParser()
        parsed = parser.parse(file_path)
        
        logger.info(f"Document parsed: {parsed.metadata}")
        
        # Chunk document
        chunker = DocumentChunker()
        chunks = chunker.chunk_document(
            parsed.content,
            metadata={
                "filename": file.filename,
                "document_id": document_id,
                "page_count": parsed.metadata.get("page_count", 0)
            }
        )
        
        logger.info(f"Created {len(chunks)} chunks")
        
        # Store in vector database
        vector_store = get_vector_store()
        chunk_contents = [chunk.content for chunk in chunks]
        chunk_metadatas = [
            {**chunk.metadata, "chunk_index": chunk.chunk_index}
            for chunk in chunks
        ]
        
        vector_store.add_documents(
            chunks=chunk_contents,
            metadatas=chunk_metadatas,
            document_id=document_id
        )
        
        logger.info(f"Document indexed: {document_id}")
        
        return UploadResponse(
            success=True,
            document_id=document_id,
            filename=file.filename,
            message="Document uploaded and indexed successfully",
            chunks_created=len(chunks),
            page_count=parsed.metadata.get("page_count")
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
