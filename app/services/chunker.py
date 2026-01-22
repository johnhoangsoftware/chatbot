from typing import List, Dict, Any
from dataclasses import dataclass
import re

from app.config import get_settings


@dataclass
class Chunk:
    """Represents a text chunk."""
    content: str
    metadata: Dict[str, Any]
    chunk_index: int


class DocumentChunker:
    """Chunk documents with semantic awareness and overlap."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
    
    def chunk_document(
        self, 
        content: str, 
        metadata: Dict[str, Any] = None
    ) -> List[Chunk]:
        """
        Chunk document content with overlap.
        Uses semantic boundaries (paragraphs, sections) when possible.
        """
        if not content.strip():
            return []
        
        # Clean and normalize content
        content = self._normalize_text(content)
        
        # Split into paragraphs first
        paragraphs = self._split_into_paragraphs(content)
        
        # Create chunks with overlap
        chunks = self._create_chunks_with_overlap(paragraphs, metadata or {})
        
        return chunks
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text content."""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        text = text.strip()
        return text
    
    def _split_into_paragraphs(self, content: str) -> List[str]:
        """Split content into paragraphs."""
        # Split on double newlines or page markers
        paragraphs = re.split(r'\n\n+|\[Page \d+\]\n', content)
        # Filter empty paragraphs
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        return paragraphs
    
    def _create_chunks_with_overlap(
        self, 
        paragraphs: List[str], 
        base_metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """Create chunks from paragraphs with overlap."""
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # If single paragraph exceeds chunk size, split it
            if para_size > self.chunk_size:
                # Flush current chunk first
                if current_chunk:
                    chunk_content = "\n\n".join(current_chunk)
                    chunks.append(Chunk(
                        content=chunk_content,
                        metadata={**base_metadata, "chunk_index": chunk_index},
                        chunk_index=chunk_index
                    ))
                    chunk_index += 1
                    current_chunk = []
                    current_size = 0
                
                # Split large paragraph
                sub_chunks = self._split_large_paragraph(para, chunk_index, base_metadata)
                for sub_chunk in sub_chunks:
                    chunks.append(sub_chunk)
                    chunk_index += 1
                continue
            
            # Check if adding this paragraph exceeds chunk size
            if current_size + para_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_content = "\n\n".join(current_chunk)
                chunks.append(Chunk(
                    content=chunk_content,
                    metadata={**base_metadata, "chunk_index": chunk_index},
                    chunk_index=chunk_index
                ))
                chunk_index += 1
                
                # Keep overlap (last paragraph for context)
                overlap_content = current_chunk[-1] if current_chunk else ""
                current_chunk = [overlap_content] if overlap_content else []
                current_size = len(overlap_content)
            
            current_chunk.append(para)
            current_size += para_size
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_content = "\n\n".join(current_chunk)
            chunks.append(Chunk(
                content=chunk_content,
                metadata={**base_metadata, "chunk_index": chunk_index},
                chunk_index=chunk_index
            ))
        
        return chunks
    
    def _split_large_paragraph(
        self, 
        paragraph: str, 
        start_index: int,
        base_metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """Split a large paragraph into smaller chunks."""
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        
        current_chunk = []
        current_size = 0
        chunk_index = start_index
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.chunk_size and current_chunk:
                chunk_content = " ".join(current_chunk)
                chunks.append(Chunk(
                    content=chunk_content,
                    metadata={**base_metadata, "chunk_index": chunk_index},
                    chunk_index=chunk_index
                ))
                chunk_index += 1
                
                # Keep last sentence for overlap
                current_chunk = [current_chunk[-1]] if current_chunk else []
                current_size = len(current_chunk[0]) if current_chunk else 0
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        if current_chunk:
            chunk_content = " ".join(current_chunk)
            chunks.append(Chunk(
                content=chunk_content,
                metadata={**base_metadata, "chunk_index": chunk_index},
                chunk_index=chunk_index
            ))
        
        return chunks
