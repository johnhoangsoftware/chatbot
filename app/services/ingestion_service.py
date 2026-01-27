# ingest_service/ingestion_service.py
"""
Main ingestion service that orchestrates the entire data pipeline.

Flow:
1. Adapter collects raw documents from source
2. Save raw documents to database
3. Chunk each raw document
4. Save chunks to database
5. Generate embeddings and save to vector store
6. Update chunk records with vector IDs
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.rag.db import get_document_db, RawDocument, DocumentChunk
from app.rag.ingrest_service.adapters import (
    BaseAdapter, 
    CollectedDocument, 
    AdapterRegistry,
    FileAdapter,
    URLAdapter
)
from app.rag.ingrest_service.chunking import chunk
from app.services.vector_store import get_vector_store
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""
    success: bool
    document_id: str
    source_type: str
    source_name: str
    chunk_count: int
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "document_id": self.document_id,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "chunk_count": self.chunk_count,
            "error": self.error
        }


class IngestionService:
    """
    Main service for ingesting documents from various sources.
    
    Handles the complete pipeline:
    - Collecting data via adapters
    - Storing raw documents in database
    - Chunking and embedding
    - Maintaining traceability
    """
    
    def __init__(self):
        self.db = get_document_db()
        self.vector_store = get_vector_store()
    
    def ingest_from_adapter(
        self, 
        adapter: BaseAdapter,
        **collect_kwargs
    ) -> List[IngestionResult]:
        """
        Ingest documents using a specific adapter.
        
        Args:
            adapter: Adapter instance to use for collection
            **collect_kwargs: Arguments to pass to adapter.collect()
            
        Returns:
            List of IngestionResult for each document
        """
        results = []
        
        try:
            # Collect documents from source
            collected_docs = adapter.collect(**collect_kwargs)
            logger.info(f"Collected {len(collected_docs)} documents from {adapter.source_type}")
            
            for doc in collected_docs:
                result = self._process_single_document(doc)
                results.append(result)
                
        except Exception as e:
            logger.error(f"Error during ingestion: {e}")
            results.append(IngestionResult(
                success=False,
                document_id="",
                source_type=adapter.source_type,
                source_name="",
                chunk_count=0,
                error=str(e)
            ))
        
        return results
    
    def ingest_file(self, file_path: str) -> IngestionResult:
        """Convenience method to ingest a single file."""
        adapter = FileAdapter(file_path=file_path)
        results = self.ingest_from_adapter(adapter)
        print("Hoang:Result", results)
        return results[0] if results else IngestionResult(
            success=False, document_id="", source_type="file",
            source_name=file_path, chunk_count=0, error="No documents collected"
        )
    
    def ingest_url(self, url: str) -> IngestionResult:
        """Convenience method to ingest from a URL."""
        adapter = URLAdapter(url=url)
        results = self.ingest_from_adapter(adapter)
        return results[0] if results else IngestionResult(
            success=False, document_id="", source_type="url",
            source_name=url, chunk_count=0, error="No documents collected"
        )
    
    def ingest_auto(self, source: str, **kwargs) -> List[IngestionResult]:
        """
        Auto-detect source type and ingest.
        
        Args:
            source: File path or URL
            **kwargs: Additional arguments
            
        Returns:
            List of IngestionResult
        """
        adapter = AdapterRegistry.detect_and_create(source, **kwargs)
        if adapter is None:
            return [IngestionResult(
                success=False, document_id="", source_type="unknown",
                source_name=source, chunk_count=0, 
                error=f"Could not detect adapter for: {source}"
            )]
        return self.ingest_from_adapter(adapter)
    
    def _process_single_document(self, doc: CollectedDocument) -> IngestionResult:
        """Process a single collected document through the pipeline."""
        try:
            # 1. Save raw document to database
            raw_doc = self.db.create_raw_document(
                source_type=doc.source_type,
                source_path=doc.source_path,
                content=doc.content,
                source_name=doc.source_name,
                metadata=doc.metadata
            )
            
            logger.info(f"Saved raw document: {raw_doc.id[:8]} ({doc.source_name})")
            
            # 2. Chunk the document
            raw_doc_dict = {
                "raw_id": raw_doc.id,
                "content": doc.content,
                "source_type": doc.source_type,
                "path": doc.source_path,
                "metadata": doc.metadata
            }
            chunks = chunk(raw_doc_dict)
            
            logger.info(f"Created {len(chunks)} chunks for doc {raw_doc.id[:8]}")
            
            # 3. Generate embeddings and add to vector store
            chunk_contents = [c["text"] for c in chunks]
            chunk_metadatas = []
            
            for c in chunks:
                meta = {
                    **c["metadata"],
                    "raw_document_id": raw_doc.id,
                    "chunk_id": c["chunk_id"],
                    "document_id": raw_doc.id,  # For compatibility
                    "filename": doc.source_name,
                }
                chunk_metadatas.append(meta)
            
            # Add to vector store
            vector_ids = self.vector_store.add_documents(
                chunks=chunk_contents,
                metadatas=chunk_metadatas,
                document_id=raw_doc.id
            )
            
            # 4. Save chunks to database with vector IDs
            chunk_records = []
            for i, c in enumerate(chunks):
                vector_id = vector_ids[i] if i < len(vector_ids) else None
                chunk_records.append({
                    "chunk_index": c["metadata"]["chunk_index"],
                    "content": c["text"],
                    "vector_id": vector_id,
                    "metadata": c["metadata"]
                })
            
            self.db.create_chunks(raw_doc.id, chunk_records)
            
            logger.info(f"Successfully ingested document: {raw_doc.id[:8]}")
            
            return IngestionResult(
                success=True,
                document_id=raw_doc.id,
                source_type=doc.source_type,
                source_name=doc.source_name,
                chunk_count=len(chunks)
            )
            
        except Exception as e:
            logger.error(f"Error processing document {doc.source_name}: {e}")
            return IngestionResult(
                success=False,
                document_id="",
                source_type=doc.source_type,
                source_name=doc.source_name,
                chunk_count=0,
                error=str(e)
            )
    
    def get_document_info(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get full document info including chunks."""
        raw_doc = self.db.get_raw_document(document_id)
        if not raw_doc:
            return None
        
        chunks = self.db.get_chunks_by_document(document_id)
        
        return {
            "document": raw_doc.to_dict(),
            "chunks": [c.to_dict() for c in chunks]
        }
    
    def delete_document(self, document_id: str) -> bool:
        """Delete document from both database and vector store."""
        # Delete from vector store
        self.vector_store.delete_document(document_id)
        
        # Delete from database (cascades to chunks)
        return self.db.delete_raw_document(document_id)


# Singleton instance
_ingestion_service: Optional[IngestionService] = None


def get_ingestion_service() -> IngestionService:
    """Get or create ingestion service instance."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
    return _ingestion_service
