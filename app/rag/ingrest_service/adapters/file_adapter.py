# ingest_service/adapters/file_adapter.py
"""
Adapter for collecting data from uploaded files (PDF, text, etc.).
"""
import os
from typing import List, Optional

from .base import BaseAdapter, CollectedDocument
from app.services.parsers import ParserFactory
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class FileAdapter(BaseAdapter):
    """
    Adapter for collecting documents from uploaded files.
    Supports PDF, DOCX, Excel, TXT, MD, and other text-based files.
    """
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.md', '.docx', '.doc', '.xlsx', '.xls'}
    
    def __init__(self, file_path: str = None, file_paths: List[str] = None):
        """
        Initialize with single file or list of files.
        
        Args:
            file_path: Single file path
            file_paths: List of file paths
        """
        self.file_paths = []
        if file_path:
            self.file_paths.append(file_path)
        if file_paths:
            self.file_paths.extend(file_paths)
    
    @property
    def source_type(self) -> str:
        return "file"
    
    def validate(self, file_path: str = None, **kwargs) -> bool:
        """Validate that files exist and are supported."""
        paths = [file_path] if file_path else self.file_paths
        
        for path in paths:
            if not os.path.exists(path):
                logger.warning(f"File not found: {path}")
                return False
            
            ext = os.path.splitext(path)[1].lower()
            if ext not in self.SUPPORTED_EXTENSIONS:
                logger.warning(f"Unsupported file type: {ext}")
                return False
        
        return True
    
    def collect(self, file_path: str = None, **kwargs) -> List[CollectedDocument]:
        """
        Collect documents from files.
        
        Args:
            file_path: Optional single file to process (overrides constructor paths)
            
        Returns:
            List of CollectedDocument objects
        """
        paths = [file_path] if file_path else self.file_paths
        results = []
        
        for path in paths:
            try:
                doc = self._collect_single_file(path)
                if doc:
                    results.append(doc)
            except Exception as e:
                logger.error(f"Error collecting file {path}: {e}")
                continue
        
        logger.info(f"FileAdapter collected {len(results)} documents")
        return results
    
    def _collect_single_file(self, file_path: str) -> Optional[CollectedDocument]:
        """Collect a single file using ParserFactory."""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        
        ext = os.path.splitext(file_path)[1].lower()
        filename = os.path.basename(file_path)
        
        try:
            # Use ParserFactory to parse the file
            parsed = ParserFactory.parse(file_path)
            content = parsed.content
            metadata = parsed.metadata
            
            # Create CollectedDocument
            return CollectedDocument(
                raw_id=self.generate_raw_id(),
                content=content,
                source_type=self.source_type,
                source_path=os.path.abspath(file_path),
                source_name=filename,
                metadata={
                    "filename": filename,
                    "file_extension": ext,
                    "file_size": os.path.getsize(file_path),
                    **metadata
                }
            )
            
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return None
