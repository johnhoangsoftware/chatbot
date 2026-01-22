"""
Database models for raw documents and chunks.
Supports traceability from chatbot responses back to source data.
"""
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, JSON, create_engine
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class RawDocument(Base):
    """
    Stores raw documents collected from various sources.
    This is the source of truth for traceability.
    """
    __tablename__ = "raw_documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Source information
    source_type = Column(String(50), nullable=False)  # "file", "github", "url", "api"
    source_path = Column(String(500), nullable=False)  # original path/url
    source_name = Column(String(255), nullable=True)   # display name (filename, repo name, etc.)
    
    # Content
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True)  # SHA256 hash for deduplication
    
    # Metadata
    doc_metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to chunks
    chunks = relationship("DocumentChunk", back_populates="raw_document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<RawDocument(id={self.id[:8]}, source_type={self.source_type}, source_name={self.source_name})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "source_type": self.source_type,
            "source_path": self.source_path,
            "source_name": self.source_name,
            "content_preview": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "doc_metadata": self.doc_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "chunk_count": len(self.chunks) if self.chunks else 0
        }


class DocumentChunk(Base):
    """
    Stores chunked portions of raw documents.
    Links to both SQLite (raw_document_id) and ChromaDB (vector_id).
    """
    __tablename__ = "document_chunks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Link to raw document
    raw_document_id = Column(String(36), ForeignKey("raw_documents.id"), nullable=False)
    
    # Chunk information
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    
    # Link to vector store
    vector_id = Column(String(100), nullable=True)  # ChromaDB document ID
    
    # Chunk metadata
    doc_metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    raw_document = relationship("RawDocument", back_populates="chunks")
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id[:8]}, raw_doc={self.raw_document_id[:8]}, index={self.chunk_index})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "raw_document_id": self.raw_document_id,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "vector_id": self.vector_id,
            "doc_metadata": self.doc_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def to_trace_dict(self):
        """Full traceability info including raw document."""
        trace = self.to_dict()
        if self.raw_document:
            trace["raw_document"] = {
                "id": self.raw_document.id,
                "source_type": self.raw_document.source_type,
                "source_path": self.raw_document.source_path,
                "source_name": self.raw_document.source_name,
                "doc_metadata": self.raw_document.doc_metadata
            }
        return trace
