import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
import uuid
import time

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

from app.config import get_settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class VectorStore:
    """ChromaDB vector store for document embeddings with flexible provider support."""
    
    COLLECTION_NAME = "automotive_docs"
    
    # Rate limit settings (only applied for API-based embeddings)
    BATCH_SIZE = 1 
    BATCH_DELAY = 1.0 
    MAX_RETRIES = 5
    RETRY_DELAY = 5.0
    
    def __init__(self):
        self.settings = get_settings()
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=self.settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        # Initialize embeddings based on provider
        self.provider = self.settings.embedding_provider.lower()
        self.embeddings = None
        
        self._init_embeddings()
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "Automotive domain documents"}
        )
        
        logger.info(f"VectorStore initialized. Provider: {self.provider}. Collection: {self.COLLECTION_NAME}")

    def _flatten_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten metadata dictionary for ChromaDB compatibility.
        ChromaDB only supports str, int, float, bool.
        Nested dicts/lists need to be converted.
        """
        flat = {}
        for k, v in metadata.items():
            if isinstance(v, (dict, list)):
                # For now, just stringify complex types
                # Alternatively we could flatten dicts like pdf_metadata.title
                import json
                try:
                    flat[k] = json.dumps(v)
                except:
                    flat[k] = str(v)
            elif v is None:
                flat[k] = ""
            else:
                flat[k] = v
        return flat

    def _init_embeddings(self):
        """Initialize appropriate embedding model."""
        if self.provider == "gemini":
            if not self.settings.google_api_key:
                logger.warning("Gemini API key missing, falling back to local embeddings")
                self.provider = "local"
                self._init_embeddings()
                return

            logger.info("Using Google Gemini Embeddings (Online)")
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=self.settings.google_api_key
            )
            
        else:  # default to local
            logger.info(f"Using Local HuggingFace Embeddings: {self.settings.embedding_model_name}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.settings.embedding_model_name
            )
            # Local embeddings don't need rate limiting
            self.BATCH_SIZE = 100 
            self.BATCH_DELAY = 0

    def _embed_with_retry(self, texts: List[str], is_query: bool = False) -> List[List[float]]:
        """Embed texts with retry logic (only relevant for API calls)."""
        if self.provider == "local":
            if is_query:
                return [self.embeddings.embed_query(texts[0])]
            return self.embeddings.embed_documents(texts)
            
        # Retry logic for API
        for attempt in range(self.MAX_RETRIES):
            try:
                if is_query:
                    return [self.embeddings.embed_query(texts[0])]
                else:
                    return self.embeddings.embed_documents(texts)
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    wait_time = self.RETRY_DELAY * (attempt + 1)
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{self.MAX_RETRIES}")
                    time.sleep(wait_time)
                else:
                    raise e
        
        raise Exception(f"Failed to embed after {self.MAX_RETRIES} retries")
    
    def _batch_embed(self, chunks: List[str]) -> List[List[float]]:
        """Embed chunks in batches."""
        all_embeddings = []
        total_batches = (len(chunks) + self.BATCH_SIZE - 1) // self.BATCH_SIZE
        
        for i in range(0, len(chunks), self.BATCH_SIZE):
            batch = chunks[i:i + self.BATCH_SIZE]
            batch_num = (i // self.BATCH_SIZE) + 1
            
            logger.info(f"Embedding batch {batch_num}/{total_batches} ({len(batch)} chunks)")
            
            # Embed
            batch_embeddings = self._embed_with_retry(batch)
            all_embeddings.extend(batch_embeddings)
            
            # Wait between batches if delay is set
            if self.BATCH_DELAY > 0 and i + self.BATCH_SIZE < len(chunks):
                time.sleep(self.BATCH_DELAY)
        
        return all_embeddings
    
    def add_documents(
        self, 
        chunks: List[str], 
        metadatas: List[Dict[str, Any]] = None,
        document_id: str = None
    ) -> List[str]:
        """Add document chunks to the vector store."""
        if not chunks:
            return []
        
        if not self.embeddings:
            raise ValueError("Embeddings not initialized.")
        
        # Generate unique IDs for chunks
        doc_id = document_id or str(uuid.uuid4())
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        
        # Add document_id to metadata
        if metadatas:
            for meta in metadatas:
                meta["document_id"] = doc_id
        else:
            metadatas = [{"document_id": doc_id, "chunk_index": i} for i in range(len(chunks))]
        
        # Flatten metadata for ChromaDB (which doesn't support nested dicts)
        flat_metadatas = [self._flatten_metadata(m) for m in metadatas]
        
        logger.info(f"Starting to embed {len(chunks)} chunks for document {doc_id}")
        
        # Generate embeddings
        embeddings = self._batch_embed(chunks)
        
        # Add to ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=flat_metadatas
        )
        
        logger.info(f"Successfully added {len(chunks)} chunks for document {doc_id}")
        return ids
    
    def search(
        self, 
        query: str, 
        k: int = 5,
        filter_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        if not self.embeddings:
            raise ValueError("Embeddings not initialized.")
        
        # Generate query embedding
        query_embedding = self._embed_with_retry([query], is_query=True)[0]
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=filter_metadata,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                formatted_results.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else None,
                    "score": 1 - results["distances"][0][i] if results["distances"] else None
                })
        
        logger.info(f"Search query: '{query[:50]}...' returned {len(formatted_results)} results")
        return formatted_results
    
    def get_documents_by_id(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document."""
        results = self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"]
        )
        
        formatted = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"]):
                formatted.append({
                    "content": doc,
                    "metadata": results["metadatas"][i] if results["metadatas"] else {}
                })
        
        return formatted
    
    def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a document."""
        try:
            # Get chunk IDs for this document
            results = self.collection.get(
                where={"document_id": document_id},
                include=[]
            )
            
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return {
            "name": self.COLLECTION_NAME,
            "count": self.collection.count(),
            "provider": self.provider
        }


# Singleton instance
_vector_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create vector store instance."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
