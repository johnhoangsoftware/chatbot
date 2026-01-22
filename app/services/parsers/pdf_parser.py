"""
PDF parser - wraps existing TechnicalDocumentParser for PDF files.
"""

import os
from typing import List
from .base import BaseParser, ParsedDocument

# Import the existing TechnicalDocumentParser
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from document_parser import TechnicalDocumentParser


class PDFParser(BaseParser):
    """Parser for PDF files using the existing TechnicalDocumentParser."""
    
    def __init__(self):
        self._parser = TechnicalDocumentParser()
    
    @property
    def supported_extensions(self) -> List[str]:
        return ['.pdf']
    
    def parse(self, file_path: str) -> ParsedDocument:
        """Parse a PDF file."""
        if not self.validate(file_path):
            raise ValueError(f"Invalid or unsupported file: {file_path}")
        
        # Delegate to existing parser
        return self._parser._parse_technical_pdf(file_path)
