"""
Parser factory for selecting the appropriate parser based on file type.
"""

import os
from typing import Optional, Type, Dict
from .base import BaseParser
from .pdf_parser import PDFParser
from .docx_parser import DOCXParser
from .excel_parser import ExcelParser
from .text_parser import TextParser


class ParserFactory:
    """
    Factory for creating parser instances based on file extension.
    """
    
    # Mapping extension -> parser class
    _extension_map: Dict[str, Type[BaseParser]] = {
        '.pdf': PDFParser,
        '.docx': DOCXParser,
        '.doc': DOCXParser,
        '.xlsx': ExcelParser,
        '.xls': ExcelParser,
        '.txt': TextParser,
        '.md': TextParser,
        '.csv': TextParser,
    }
    
    @classmethod
    def get_parser(cls, file_path: str) -> Optional[BaseParser]:
        """
        Get the appropriate parser for a file.

        Returns a NEW parser instance or None if no parser found
        """
        ext = os.path.splitext(file_path)[1].lower()
        parser_class = cls._extension_map.get(ext)
        if parser_class:
            return parser_class()
        return None
    
    @classmethod
    def parse(cls, file_path: str):
        """
        Parse a file using the appropriate parser.
        """
        parser = cls.get_parser(file_path)
        if parser is None:
            ext = os.path.splitext(file_path)[1]
            raise ValueError(f"No parser available for file type: {ext}")
        
        return parser.parse(file_path)