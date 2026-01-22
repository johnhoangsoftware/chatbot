# routers/traceability.py
"""
Traceability API endpoints.
Allows tracing from chatbot responses back to source documents.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.rag.db import get_document_db
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


class ChunkTraceResponse(BaseModel):
    """Response model for chunk trace."""
    chunk_id: str
    raw_document_id: str
    chunk_index: int
    content: str
    vector_id: Optional[str]
    metadata: Dict[str, Any]
    raw_document: Optional[Dict[str, Any]]


class DocumentTraceResponse(BaseModel):
    """Response model for document trace."""
    document_id: str
    source_type: str
    source_path: str
    source_name: str
    content_preview: str
    metadata: Dict[str, Any]
    created_at: str
    chunks: List[Dict[str, Any]]


@router.get("/chunk/{chunk_id}", response_model=ChunkTraceResponse)
async def trace_chunk(chunk_id: str):
    """
    Trace a chunk back to its source.
    
    Given a chunk_id (from chatbot response sources), returns:
    - Full chunk content
    - Raw document information
    - Source metadata
    """
    db = get_document_db()
    
    chunk = db.get_chunk(chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    return ChunkTraceResponse(
        chunk_id=chunk.id,
        raw_document_id=chunk.raw_document_id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        vector_id=chunk.vector_id,
        metadata=chunk.doc_metadata or {},
        raw_document=chunk.raw_document.to_dict() if chunk.raw_document else None
    )


@router.get("/chunk/by-vector/{vector_id}", response_model=ChunkTraceResponse)
async def trace_chunk_by_vector_id(vector_id: str):
    """
    Trace a chunk by its vector store ID.
    
    Useful when you have the vector ID from ChromaDB search results.
    """
    db = get_document_db()
    
    chunk = db.get_chunk_by_vector_id(vector_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found for vector ID")
    
    return ChunkTraceResponse(
        chunk_id=chunk.id,
        raw_document_id=chunk.raw_document_id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        vector_id=chunk.vector_id,
        metadata=chunk.doc_metadata or {},
        raw_document=chunk.raw_document.to_dict() if chunk.raw_document else None
    )


@router.get("/document/{document_id}", response_model=DocumentTraceResponse)
async def trace_document(document_id: str):
    """
    Get full document info with all chunks.
    
    Returns the raw document and all its chunks.
    """
    db = get_document_db()
    
    raw_doc = db.get_raw_document(document_id)
    if not raw_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    chunks = db.get_chunks_by_document(document_id)
    
    content_preview = raw_doc.content[:500] + "..." if len(raw_doc.content) > 500 else raw_doc.content
    
    return DocumentTraceResponse(
        document_id=raw_doc.id,
        source_type=raw_doc.source_type,
        source_path=raw_doc.source_path,
        source_name=raw_doc.source_name or "",
        content_preview=content_preview,
        metadata=raw_doc.doc_metadata or {},
        created_at=raw_doc.created_at.isoformat() if raw_doc.created_at else "",
        chunks=[c.to_dict() for c in chunks]
    )


@router.get("/document/{document_id}/content")
async def get_document_content(document_id: str):
    """Get full document content (raw text)."""
    db = get_document_db()
    
    raw_doc = db.get_raw_document(document_id)
    if not raw_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "document_id": raw_doc.id,
        "source_name": raw_doc.source_name,
        "content": raw_doc.content
    }


@router.get("/stats")
async def get_traceability_stats():
    """Get database statistics."""
    db = get_document_db()
    return db.get_stats()


@router.get("/documents")
async def list_documents(source_type: str = None, limit: int = 100):
    """List all documents with optional filtering."""
    db = get_document_db()
    
    docs = db.list_raw_documents(source_type=source_type, limit=limit)
    
    return {
        "total": len(docs),
        "documents": [doc.to_dict() for doc in docs]
    }
