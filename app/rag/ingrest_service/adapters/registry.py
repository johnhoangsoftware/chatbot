# ingest_service/adapters/registry.py
"""
Adapter Registry for managing and discovering adapters.
Provides factory methods for creating adapters based on source type.
"""
from typing import Dict, Type, Optional, List

from .base import BaseAdapter, CollectedDocument
from .file_adapter import FileAdapter
from .url_adapter import URLAdapter
from .github_adapter import GitHubAdapter
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class AdapterRegistry:
    """
    Registry for managing data collection adapters.
    
    Provides:
    - Registration of new adapter types
    - Factory methods for creating adapters
    - Auto-detection of adapter type based on source
    """
    
    _adapters: Dict[str, Type[BaseAdapter]] = {}
    
    @classmethod
    def register(cls, source_type: str, adapter_class: Type[BaseAdapter]):
        """Register an adapter class for a source type."""
        cls._adapters[source_type] = adapter_class
        logger.info(f"Registered adapter: {source_type} -> {adapter_class.__name__}")
    
    @classmethod
    def get_adapter_class(cls, source_type: str) -> Optional[Type[BaseAdapter]]:
        """Get adapter class by source type."""
        return cls._adapters.get(source_type)
    
    @classmethod
    def list_adapters(cls) -> List[str]:
        """List all registered source types."""
        return list(cls._adapters.keys())
    
    @classmethod
    def create_adapter(cls, source_type: str, **kwargs) -> Optional[BaseAdapter]:
        """
        Factory method to create an adapter instance.
        
        Args:
            source_type: Type of source (file, url, github)
            **kwargs: Arguments to pass to adapter constructor
            
        Returns:
            Adapter instance or None if not found
        """
        adapter_class = cls.get_adapter_class(source_type)
        if adapter_class is None:
            logger.error(f"No adapter registered for source type: {source_type}")
            return None
        
        return adapter_class(**kwargs)
    
    @classmethod
    def detect_and_create(cls, source: str, **kwargs) -> Optional[BaseAdapter]:
        """
        Auto-detect source type and create appropriate adapter.
        
        Args:
            source: Path, URL, or other source identifier
            **kwargs: Additional arguments for adapter
            
        Returns:
            Appropriate adapter instance
        """
        import os
        from urllib.parse import urlparse
        
        # Check if it's a file path
        if os.path.exists(source):
            return cls.create_adapter("file", file_path=source, **kwargs)
        
        # Check if it's a URL
        try:
            parsed = urlparse(source)
            if parsed.scheme in ('http', 'https'):
                # Check for GitHub
                if 'github.com' in parsed.netloc:
                    return cls.create_adapter("github", repo_url=source, **kwargs)
                # General URL
                return cls.create_adapter("url", url=source, **kwargs)
        except:
            pass
        
        logger.warning(f"Could not detect adapter type for: {source}")
        return None


# Register default adapters
AdapterRegistry.register("file", FileAdapter)
AdapterRegistry.register("url", URLAdapter)
AdapterRegistry.register("github", GitHubAdapter)
