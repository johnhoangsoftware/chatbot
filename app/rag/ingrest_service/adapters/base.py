# ingest_service/adapters/base.py
"""
Base adapter class for data collection from various sources.
All adapters must implement the collect() method.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class CollectedDocument:
    """Represents a document collected from a source."""
    raw_id: str
    content: str
    source_type: str
    source_path: str
    source_name: str
    metadata: Dict[str, Any]
    collected_at: datetime = None
    
    def __post_init__(self):
        if self.collected_at is None:
            self.collected_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_id": self.raw_id,
            "content": self.content,
            "source_type": self.source_type,
            "source_path": self.source_path,
            "source_name": self.source_name,
            "metadata": self.metadata,
            "collected_at": self.collected_at.isoformat()
        }


class BaseAdapter(ABC):
    """
    Abstract base class for data collection adapters.
    
    Each adapter handles collecting data from a specific source type
    (e.g., files, GitHub, URLs, APIs).
    """
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the source type identifier (e.g., 'file', 'github', 'url')."""
        pass
    
    @abstractmethod
    def collect(self, **kwargs) -> List[CollectedDocument]:
        """
        Collect documents from the source.
        
        Returns:
            List of CollectedDocument objects ready for storage and chunking.
        """
        pass
    
    @abstractmethod
    def validate(self, **kwargs) -> bool:
        """
        Validate that the source is accessible and valid.
        
        Returns:
            True if the source is valid and accessible.
        """
        pass
    
    def generate_raw_id(self) -> str:
        """Generate a unique raw document ID."""
        return uuid.uuid4().hex

