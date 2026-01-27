from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import uuid
import shutil
import requests

from app.config import get_settings
from app.services.ingestion_service import get_ingestion_service
from app.services.vector_store import get_vector_store
from app.rag.ingrest_service.adapters import GitHubAdapter, JiraAdapter
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
    type: Optional[str] = "url, github, jira, confluence"
    url: str


class GitHubConnectionRequest(BaseModel):
    """Request model for testing GitHub connection."""
    repo_url: str
    github_token: Optional[str] = None


class JiraConnectionRequest(BaseModel):
    """Request model for testing Jira connection."""
    jira_url: str
    email: str
    api_token: str


class ConnectionResponse(BaseModel):
    """Response model for connection test."""
    success: bool
    message: str
    details: Optional[dict] = None



@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    """
    Upload and process a document using ingress service FileAdapter.
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
        
        if is_github or request.type == "github":
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


@router.post("/test-github-connection", response_model=ConnectionResponse)
async def test_github_connection(request: GitHubConnectionRequest):
    """
    Test connection to GitHub repository.
    Checks if repository is accessible and returns basic info.
    """
    try:
        # Parse repo URL
        parts = request.repo_url.rstrip('/').split('/')
        if len(parts) < 2:
            raise HTTPException(
                status_code=400,
                detail="Invalid GitHub URL format"
            )
        
        owner = parts[-2]
        repo = parts[-1].replace('.git', '')
        
        # Test API connection
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'RAG-Ingestion-Service'
        }
        
        if request.github_token:
            headers['Authorization'] = f'token {request.github_token}'
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            return ConnectionResponse(
                success=False,
                message="Repository not found or is private",
                details={
                    "status_code": 404,
                    "repo": f"{owner}/{repo}"
                }
            )
        
        if response.status_code == 403:
            return ConnectionResponse(
                success=False,
                message="Rate limit exceeded or access forbidden. Try adding a GitHub token.",
                details={
                    "status_code": 403,
                    "repo": f"{owner}/{repo}"
                }
            )
        
        if response.status_code != 200:
            return ConnectionResponse(
                success=False,
                message=f"GitHub API error: {response.status_code}",
                details={
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
            )
        
        repo_data = response.json()
        
        return ConnectionResponse(
            success=True,
            message="Successfully connected to GitHub repository",
            details={
                "repo_name": repo_data.get('full_name'),
                "description": repo_data.get('description'),
                "default_branch": repo_data.get('default_branch'),
                "stars": repo_data.get('stargazers_count'),
                "language": repo_data.get('language'),
                "size_kb": repo_data.get('size'),
                "private": repo_data.get('private'),
                "updated_at": repo_data.get('updated_at')
            }
        )
    
    except requests.exceptions.Timeout:
        return ConnectionResponse(
            success=False,
            message="Connection timeout. Please check your internet connection.",
            details={"error": "timeout"}
        )
    
    except requests.exceptions.RequestException as e:
        return ConnectionResponse(
            success=False,
            message=f"Network error: {str(e)}",
            details={"error": str(e)}
        )
    
    except Exception as e:
        logger.error(f"Error testing GitHub connection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error testing connection: {str(e)}"
        )


@router.post("/test-jira-connection", response_model=ConnectionResponse)
async def test_jira_connection(request: JiraConnectionRequest):
    """
    Test connection to Jira instance.
    Validates credentials and returns user info.
    """
    try:
        jira_url = request.jira_url.rstrip('/')
        
        # Test connection with /myself endpoint
        api_url = f"{jira_url}/rest/api/3/myself"
        
        response = requests.get(
            api_url,
            auth=(request.email, request.api_token),
            headers={'Accept': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 401:
            return ConnectionResponse(
                success=False,
                message="Authentication failed. Please check your email and API token.",
                details={
                    "status_code": 401,
                    "jira_url": jira_url
                }
            )
        
        if response.status_code == 403:
            return ConnectionResponse(
                success=False,
                message="Access forbidden. Your account may not have sufficient permissions.",
                details={
                    "status_code": 403,
                    "jira_url": jira_url
                }
            )
        
        if response.status_code == 404:
            return ConnectionResponse(
                success=False,
                message="Jira instance not found. Please check the URL.",
                details={
                    "status_code": 404,
                    "jira_url": jira_url,
                    "hint": "Make sure to use the correct Jira URL (e.g., https://your-domain.atlassian.net)"
                }
            )
        
        if response.status_code != 200:
            return ConnectionResponse(
                success=False,
                message=f"Jira API error: {response.status_code}",
                details={
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
            )
        
        user_data = response.json()
        
        # Test search endpoint to verify permissions
        search_url = f"{jira_url}/rest/api/3/search"
        search_response = requests.get(
            search_url,
            auth=(request.email, request.api_token),
            headers={'Accept': 'application/json'},
            params={'jql': 'ORDER BY created DESC', 'maxResults': 1},
            timeout=10
        )
        
        can_search = search_response.status_code == 200
        
        return ConnectionResponse(
            success=True,
            message="Successfully connected to Jira",
            details={
                "account_id": user_data.get('accountId'),
                "display_name": user_data.get('displayName'),
                "email": user_data.get('emailAddress'),
                "active": user_data.get('active'),
                "account_type": user_data.get('accountType'),
                "timezone": user_data.get('timeZone'),
                "can_search_issues": can_search,
                "jira_url": jira_url
            }
        )
    
    except requests.exceptions.Timeout:
        return ConnectionResponse(
            success=False,
            message="Connection timeout. Please check your internet connection or Jira URL.",
            details={"error": "timeout"}
        )
    
    except requests.exceptions.RequestException as e:
        return ConnectionResponse(
            success=False,
            message=f"Network error: {str(e)}",
            details={"error": str(e)}
        )
    
    except Exception as e:
        logger.error(f"Error testing Jira connection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error testing connection: {str(e)}"
        )

