"""
Database service for document storage and retrieval.
Provides CRUD operations for RawDocument and DocumentChunk models.
"""
import os
import hashlib
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import get_settings
from app.rag.db.models import Base, RawDocument, DocumentChunk
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class DocumentDatabase:
    """Database service for raw documents and chunks."""
    
    def __init__(self, db_path: str = None):
        settings = get_settings()
        
        if db_path is None:
            db_dir = os.path.join(settings.chroma_persist_dir, "..")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "documents.db")
        
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        
        # Create tables
        Base.metadata.create_all(self.engine)
        
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info(f"DocumentDatabase initialized: {db_path}")
    
    @contextmanager
    def get_session(self) -> Session:
        """Get database session context manager."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    # =============== RawDocument CRUD ===============
    
    def create_raw_document(
        self,
        source_type: str,
        source_path: str,
        content: str,
        source_name: str = None,
        metadata: Dict[str, Any] = None
    ) -> RawDocument:
        """Create a new raw document."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        with self.get_session() as session:
            doc = RawDocument(
                source_type=source_type,
                source_path=source_path,
                source_name=source_name or os.path.basename(source_path),
                content=content,
                content_hash=content_hash,
                doc_metadata=metadata or {}
            )
            session.add(doc)
            session.flush()
            
            # Refresh to get the ID before session closes
            doc_dict = doc.to_dict()
            doc_id = doc.id
            
            logger.info(f"Created RawDocument: {doc_id[:8]} ({source_type}: {source_name})")
            
        # Return fresh object from new session
        return self.get_raw_document(doc_id)
    
    def get_raw_document(self, doc_id: str) -> Optional[RawDocument]:
        """Get raw document by ID."""
        with self.get_session() as session:
            doc = session.query(RawDocument).filter(RawDocument.id == doc_id).first()
            if doc:
                session.expunge(doc)
            return doc
    
    def get_raw_document_by_hash(self, content_hash: str) -> Optional[RawDocument]:
        """Get raw document by content hash (for deduplication)."""
        with self.get_session() as session:
            doc = session.query(RawDocument).filter(
                RawDocument.content_hash == content_hash
            ).first()
            if doc:
                session.expunge(doc)
            return doc
    
    def list_raw_documents(
        self, 
        source_type: str = None,
        limit: int = 100
    ) -> List[RawDocument]:
        """List raw documents with optional filtering."""
        with self.get_session() as session:
            query = session.query(RawDocument)
            if source_type:
                query = query.filter(RawDocument.source_type == source_type)
            docs = query.order_by(RawDocument.created_at.desc()).limit(limit).all()
            for doc in docs:
                session.expunge(doc)
            return docs
    
    def delete_raw_document(self, doc_id: str) -> bool:
        """Delete raw document and all its chunks."""
        with self.get_session() as session:
            doc = session.query(RawDocument).filter(RawDocument.id == doc_id).first()
            if doc:
                session.delete(doc)
                logger.info(f"Deleted RawDocument: {doc_id[:8]}")
                return True
            return False
    
    # =============== DocumentChunk CRUD ===============
    
    def create_chunks(
        self,
        raw_document_id: str,
        chunks: List[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """Create multiple chunks for a raw document."""
        with self.get_session() as session:
            chunk_objects = []
            for chunk_data in chunks:
                chunk = DocumentChunk(
                    raw_document_id=raw_document_id,
                    chunk_index=chunk_data.get("chunk_index", 0),
                    content=chunk_data["content"],
                    vector_id=chunk_data.get("vector_id"),
                    doc_metadata=chunk_data.get("metadata", {})
                )
                session.add(chunk)
                chunk_objects.append(chunk)
            
            session.flush()
            chunk_ids = [c.id for c in chunk_objects]
            logger.info(f"Created {len(chunk_objects)} chunks for doc {raw_document_id[:8]}")
        
        return self.get_chunks_by_document(raw_document_id)
    
    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """Get chunk by ID with raw document info."""
        with self.get_session() as session:
            chunk = session.query(DocumentChunk).filter(
                DocumentChunk.id == chunk_id
            ).first()
            if chunk:
                # Load the relationship before expunging
                _ = chunk.raw_document
                session.expunge_all()
            return chunk
    
    def get_chunk_by_vector_id(self, vector_id: str) -> Optional[DocumentChunk]:
        """Get chunk by vector store ID (for traceability from chatbot)."""
        with self.get_session() as session:
            chunk = session.query(DocumentChunk).filter(
                DocumentChunk.vector_id == vector_id
            ).first()
            if chunk:
                _ = chunk.raw_document
                session.expunge_all()
            return chunk
    
    def get_chunks_by_document(self, raw_document_id: str) -> List[DocumentChunk]:
        """Get all chunks for a raw document."""
        with self.get_session() as session:
            chunks = session.query(DocumentChunk).filter(
                DocumentChunk.raw_document_id == raw_document_id
            ).order_by(DocumentChunk.chunk_index).all()
            for chunk in chunks:
                session.expunge(chunk)
            return chunks
    
    def update_chunk_vector_id(self, chunk_id: str, vector_id: str) -> bool:
        """Update chunk's vector store ID after embedding."""
        with self.get_session() as session:
            chunk = session.query(DocumentChunk).filter(
                DocumentChunk.id == chunk_id
            ).first()
            if chunk:
                chunk.vector_id = vector_id
                return True
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_session() as session:
            doc_count = session.query(RawDocument).count()
            chunk_count = session.query(DocumentChunk).count()
            
            # Count by source type
            source_stats = {}
            for doc in session.query(RawDocument.source_type).distinct():
                count = session.query(RawDocument).filter(
                    RawDocument.source_type == doc.source_type
                ).count()
                source_stats[doc.source_type] = count
            
            return {
                "total_documents": doc_count,
                "total_chunks": chunk_count,
                "documents_by_source": source_stats
            }


# Singleton instance
_db_instance: Optional[DocumentDatabase] = None


def get_document_db() -> DocumentDatabase:
    """Get or create document database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DocumentDatabase()
    return _db_instance
