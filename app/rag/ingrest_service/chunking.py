# ingest_service/chunking.py
# fast chunking of documents
from enum import Enum
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter, CharacterTextSplitter
import re


class ChunkingStrategy(Enum):
    RECURSIVE = "recursive"
    FIXED = "fixed"
    SEMANTIC = "semantic"  # Basic semantic splitting by paragraph/structure


class ChunkerFactory:
    """Factory for creating text splitters based on strategy."""
    
    @staticmethod
    def get_splitter(strategy: str, chunk_size: int = 1000, chunk_overlap: int = 200):
        if strategy == ChunkingStrategy.FIXED.value:
            return CharacterTextSplitter(
                separator="\n",
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                keep_separator=True
            )
        elif strategy == ChunkingStrategy.SEMANTIC.value:
            # Semantic-ish: tries to split by double newlines (paragraphs) first
            # fallback to single newlines, then sentences
            return RecursiveCharacterTextSplitter(
                separators=["\n\n", "\n", ".", "?", "!", " ", ""],
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                keep_separator=True
            )
        else:
            # Default Recursive
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", " ", ""],
                keep_separator=True
            )


def chunk(
    raw_doc: Dict[str, Any], 
    strategy: str = "recursive", 
    chunk_size: int = 1000, 
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Chunk a document using the specified strategy.
    
    Args:
        raw_doc: Document dictionary with 'content', 'raw_id', 'metadata'
        strategy: Chunking strategy ('recursive', 'fixed', 'semantic')
        chunk_size: Target size of chunks
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of chunk dictionaries
    """
    splitter = ChunkerFactory.get_splitter(strategy, chunk_size, chunk_overlap)
    
    # Special handling for requirement documents if "semantic" is chosen
    content = raw_doc["content"]
    
    # If content has [Page X] markers, we might want to ensure they stick to content?
    # For now, standard splitting is usually fine as long as overlap is sufficient.
    
    chunks = splitter.split_text(content)
    output = []

    for idx, text in enumerate(chunks):
        # Create metadata for this chunk
        chunk_metadata = raw_doc.get("metadata", {}).copy()
        chunk_metadata.update({
            "chunk_index": idx,
            "source_type": raw_doc.get("source_type", "unknown"),
            "path": raw_doc.get("path", ""),
            "strategy": strategy
        })
        
        output.append({
            "chunk_id": f"{raw_doc.get('raw_id', 'unknown')}_c{idx}",
            "raw_id": raw_doc.get("raw_id"),
            "text": text,
            "metadata": chunk_metadata
        })
        
    return output

