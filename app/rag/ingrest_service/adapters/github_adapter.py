# ingest_service/adapters/github_adapter.py
"""
Adapter for collecting data from GitHub repositories.
"""
import os
import shutil
import stat
from typing import List, Optional

from git import Repo

from .base import BaseAdapter, CollectedDocument
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def _remove_readonly(func, path, excinfo):
    """
    Error handler for Windows readonly file removal.
    This fixes 'Access Denied' errors when deleting Git repos on Windows.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _rmtree_windows(path):
    """
    Robust removal of directory tree on Windows.
    Handles readonly files commonly found in Git repositories.
    """
    if not os.path.exists(path):
        return
    
    try:
        shutil.rmtree(path, onerror=_remove_readonly)
    except Exception as e:
        logger.warning(f"Failed to remove directory {path}: {e}")


class GitHubAdapter(BaseAdapter):
    """
    Adapter for collecting documents from GitHub repositories.
    Clones the repository and extracts text files.
    """
    
    ALLOWED_EXTENSIONS = {".md", ".txt", ".py", ".java", ".c", ".cpp", ".js", ".ts", ".rst"}
    
    def __init__(self, repo_url: str, branch: str = "main", tmp_dir: str = "./tmp_repo"):
        """
        Initialize GitHub adapter.
        
        Args:
            repo_url: GitHub repository URL
            branch: Branch to clone (default: main)
            tmp_dir: Temporary directory for cloning
        """
        self.repo_url = repo_url
        self.branch = branch
        self.tmp_dir = tmp_dir
    
    @property
    def source_type(self) -> str:
        return "github"
    
    def validate(self, **kwargs) -> bool:
        """Validate that the repository URL is valid."""
        if not self.repo_url:
            return False
        return "github.com" in self.repo_url or "gitlab.com" in self.repo_url
    
    def collect(self, **kwargs) -> List[CollectedDocument]:
        """
        Clone repository and collect text files.
        
        Returns:
            List of CollectedDocument objects
        """
        results = []
        
        try:
            # Clean up existing tmp directory
            _rmtree_windows(self.tmp_dir)
            
            # Clone repository
            logger.info(f"Cloning repository: {self.repo_url}")
            Repo.clone_from(self.repo_url, self.tmp_dir, branch=self.branch)
            
            # Walk through files
            for root, _, files in os.walk(self.tmp_dir):
                # Skip .git directory
                if '.git' in root:
                    continue
                
                for filename in files:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext not in self.ALLOWED_EXTENSIONS:
                        continue
                    
                    full_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(full_path, self.tmp_dir)
                    
                    try:

                        #todo update thanh doc content file cúa minh
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        
                        if not content.strip():
                            continue
                        
                        doc = CollectedDocument(
                            raw_id=self.generate_raw_id(),
                            content=content,
                            source_type=self.source_type,
                            source_path=f"{self.repo_url}/blob/{self.branch}/{relative_path}",
                            source_name=filename,
                            metadata={
                                "repo_url": self.repo_url,
                                "branch": self.branch,
                                "file_path": relative_path,
                                "file_extension": ext,
                                "file_size": len(content)
                            }
                        )
                        results.append(doc)
                        
                    except Exception as e:
                        logger.warning(f"Error reading file {full_path}: {e}")
                        continue
            
            logger.info(f"GitHubAdapter collected {len(results)} documents from {self.repo_url}")
            
        except Exception as e:
            logger.error(f"Error cloning repository {self.repo_url}: {e}")
        
        finally:
            # Cleanup
            _rmtree_windows(self.tmp_dir)
        
        return results

