"""
Document parsers for various file formats.

This package provides a modular, extensible architecture for parsing
different document types. Each parser implements the BaseParser interface
and returns a ParsedDocument object.
"""

from .base import BaseParser, ParsedDocument, TableData, Section
from .parser_factory import ParserFactory
from .pdf_parser import PDFParser
from .docx_parser import DOCXParser
from .excel_parser import ExcelParser
from .text_parser import TextParser

__all__ = [
    "BaseParser",
    "ParsedDocument",
    "TableData",
    "Section",
    "ParserFactory",
    "PDFParser",
    "DOCXParser",
    "ExcelParser",
    "TextParser",
]
