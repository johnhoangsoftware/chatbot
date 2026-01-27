"""
Base classes and data structures for document parsers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class TableData:
    """Represents extracted table data."""
    page_number: int
    content: str
    rows: int
    columns: int


@dataclass
class Section:
    """Represents a document section."""
    title: str
    level: int  # 1 = H1, 2 = H2, etc.
    content: str
    page_number: int


@dataclass
class ParsedDocument:
    """Represents a parsed document with rich metadata."""
    filename: str
    content: str
    pages: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    sections: List[Section] = field(default_factory=list)
    tables: List[TableData] = field(default_factory=list)
    toc: List[Dict[str, Any]] = field(default_factory=list)


class BaseParser(ABC):
    """
    Abstract base class for document parsers.
    
    All parsers must implement the parse() method and return a ParsedDocument.
    """
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions (e.g., ['.pdf', '.docx'])."""
        pass
    
    @abstractmethod
    def parse(self, file_path: str) -> ParsedDocument:
        """
        Parse a document and return structured content.
        
        Args:
            file_path: Absolute path to the file to parse
            
        Returns:
            ParsedDocument with extracted content and metadata
            
        Raises:
            ValueError: If file type is not supported
            FileNotFoundError: If file doesn't exist
        """
        pass
    
    def validate(self, file_path: str) -> bool:
        """
        Validate that the file can be parsed.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file is valid and can be parsed
        """
        import os
        
        if not os.path.exists(file_path):
            return False
        
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_extensions
