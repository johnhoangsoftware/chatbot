"""
Simple text file parser for .txt and .md files.
"""

import os
from typing import List
from .base import BaseParser, ParsedDocument


class TextParser(BaseParser):
    """Parser for plain text and markdown files."""
    
    @property
    def supported_extensions(self) -> List[str]:
        return ['.txt', '.md', '.rst']
    
    def parse(self, file_path: str) -> ParsedDocument:
        """Parse a text file."""
        if not self.validate(file_path):
            raise ValueError(f"Invalid or unsupported file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Create a simple "page" for the entire content
        pages = [{
            "page_number": 1,
            "content": content,
            "word_count": len(content.split()),
            "char_count": len(content),
            "has_tables": False,
            "has_figures": False,
            "sections": []
        }]
        
        metadata = {
            "filename": os.path.basename(file_path),
            "file_path": file_path,
            "page_count": 1,
            "total_words": len(content.split()),
            "total_chars": len(content),
            "table_count": 0,
            "section_count": 0,
            "has_toc": False,
            "document_type": "Text Document"
        }
        
        return ParsedDocument(
            filename=os.path.basename(file_path),
            content=content,
            pages=pages,
            metadata=metadata,
            sections=[],
            tables=[],
            toc=[]
        )
