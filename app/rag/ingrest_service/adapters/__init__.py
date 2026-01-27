# ingest_service/adapters/__init__.py
"""
Data collection adapters for various sources.
"""
from .base import BaseAdapter, CollectedDocument
from .file_adapter import FileAdapter
from .url_adapter import URLAdapter
from .github_adapter import GitHubAdapter
from .jira_adapter import JiraAdapter
from .registry import AdapterRegistry

__all__ = [
    "BaseAdapter",
    "CollectedDocument",
    "FileAdapter",
    "URLAdapter",
    "GitHubAdapter",
    "JiraAdapter",
    "AdapterRegistry"
]
