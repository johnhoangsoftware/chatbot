"""
Parser factory for selecting the appropriate parser based on file type.
"""

import os
from typing import Optional
from .base import BaseParser
from .pdf_parser import PDFParser
from .docx_parser import DOCXParser
from .excel_parser import ExcelParser
from .text_parser import TextParser


class ParserFactory:
    """
    Factory for creating parser instances based on file extension.
    """
    
    # Registry of parsers
    _parsers = [
        PDFParser(),
        DOCXParser(),
        ExcelParser(),
        TextParser(),
    ]
    
    @classmethod
    def get_parser(cls, file_path: str) -> Optional[BaseParser]:
        """
        Get the appropriate parser for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Parser instance or None if no parser found
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        for parser in cls._parsers:
            if ext in parser.supported_extensions:
                return parser
        
        return None
    
    @classmethod
    def parse(cls, file_path: str):
        """
        Parse a file using the appropriate parser.
        
        Args:
            file_path: Path to the file
            
        Returns:
            ParsedDocument
            
        Raises:
            ValueError: If no parser available for file type
        """
        parser = cls.get_parser(file_path)
        if parser is None:
            ext = os.path.splitext(file_path)[1]
            raise ValueError(f"No parser available for file type: {ext}")
        
        return parser.parse(file_path)
