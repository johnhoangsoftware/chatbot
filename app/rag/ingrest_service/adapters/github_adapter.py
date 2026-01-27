# ingest_service/adapters/github_adapter.py
"""
Adapter for collecting data from GitHub repositories.
"""
import os
import shutil
import stat
import requests
import base64
import time
from typing import List, Optional

from git import Repo

from .base import BaseAdapter, CollectedDocument
from app.services.parsers.parser_factory import ParserFactory
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
    Uses GitHub API to fetch files without cloning.
    """
    
    ALLOWED_EXTENSIONS = {".md", ".txt", ".py", ".java", ".c", ".cpp", ".js", ".ts", ".rst", ".pdf", ".docx", ".doc"}
    
    def __init__(self, repo_url: str, branch: str = "main", tmp_dir: str = "./tmp_repo", use_api: bool = True, github_token: Optional[str] = None):
        """
        Initialize GitHub adapter.
        
        Args:
            repo_url: GitHub repository URL
            branch: Branch to fetch (default: main)
            tmp_dir: Temporary directory for cloning (if use_api=False)
            use_api: Use GitHub API instead of cloning (default: True)
            github_token: Optional GitHub token for API rate limits (user provided)
        """
        self.repo_url = repo_url
        self.branch = branch
        self.tmp_dir = tmp_dir
        self.use_api = use_api
        self.github_token = github_token  # User must provide explicitly
    
    @property
    def source_type(self) -> str:
        return "github"
    
    def validate(self, **kwargs) -> bool:
        """Validate that the repository URL is valid."""
        if not self.repo_url:
            return False
        return "github.com" in self.repo_url or "gitlab.com" in self.repo_url
    
    def _parse_repo_url(self) -> tuple:
        """Parse GitHub URL to extract owner and repo name."""
        parts = self.repo_url.rstrip('/').split('/')
        if len(parts) < 2:
            raise ValueError(f"Invalid GitHub URL: {self.repo_url}")
        return parts[-2], parts[-1].replace('.git', '')
    
    def _get_api_headers(self) -> dict:
        """Get headers for GitHub API requests."""
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'RAG-Ingestion-Service'
        }
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        return headers
    
    def _fetch_repo_tree(self, owner: str, repo: str) -> List[dict]:
        """Fetch repository file tree via GitHub API."""
        api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{self.branch}"
        params = {'recursive': '1'}
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(api_url, headers=self._get_api_headers(), params=params, timeout=30)
                
                if response.status_code == 403 and 'rate limit' in response.text.lower():
                    logger.warning("GitHub API rate limit reached. Add GITHUB_TOKEN to increase limit.")
                    raise Exception("GitHub API rate limit exceeded")
                
                if response.status_code == 404:
                    # Try alternative branch names
                    if self.branch == "main" and attempt == 0:
                        logger.info("Branch 'main' not found, trying 'master'...")
                        self.branch = "master"
                        continue
                    raise Exception(f"Repository or branch not found: {owner}/{repo} (branch: {self.branch})")
                
                response.raise_for_status()
                return response.json().get('tree', [])
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"API request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to fetch repository tree after {max_retries} attempts: {e}")
        
        return []
    
    def _download_file_content(self, owner: str, repo: str, file_path: str) -> Optional[str]:
        """Download content of a single file via GitHub API."""
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
        params = {'ref': self.branch}
        
        try:
            response = requests.get(api_url, headers=self._get_api_headers(), params=params, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Failed to download {file_path}: {response.status_code}")
                return None
            
            data = response.json()
            
            # Content is base64 encoded
            if 'content' in data:
                content = base64.b64decode(data['content']).decode('utf-8', errors='ignore')
                return content
            
        except Exception as e:
            logger.warning(f"Error downloading file {file_path}: {e}")
        
        return None
    
    def _collect_via_api(self, **kwargs) -> List[CollectedDocument]:
        """Collect documents using GitHub API (no cloning required)."""
        results = []
        
        try:
            owner, repo = self._parse_repo_url()
            logger.info(f"Fetching repository via API: {owner}/{repo} (branch: {self.branch})")
            
            # Get repository tree
            tree = self._fetch_repo_tree(owner, repo)
            logger.info(f"Found {len(tree)} items in repository tree")
            
            # Filter and download files
            file_count = 0
            for item in tree:
                if item['type'] != 'blob':  # Skip directories
                    continue
                
                file_path = item['path']
                ext = os.path.splitext(file_path)[1].lower()
                
                if ext not in self.ALLOWED_EXTENSIONS:
                    continue
                
                # Download file content
                content = self._download_file_content(owner, repo, file_path)
                
                if not content or not content.strip():
                    continue
                
                file_count += 1
                filename = os.path.basename(file_path)
                
                # Extract chunk config if provided
                chunk_config = kwargs.get("chunk_config", {})
                
                doc = CollectedDocument(
                    raw_id=self.generate_raw_id(),
                    content=content,
                    source_type=self.source_type,
                    source_path=f"{self.repo_url}/blob/{self.branch}/{file_path}",
                    source_name=filename,
                    metadata={
                        "repo_url": self.repo_url,
                        "branch": self.branch,
                        "file_path": file_path,
                        "file_extension": ext,
                        "file_size": len(content),
                        "chunk_config": chunk_config
                    }
                )
                results.append(doc)
                
                logger.info(f"[{file_count}] Downloaded: {file_path} ({len(content)} chars)")
            
            logger.info(f"GitHubAdapter collected {len(results)} documents from {owner}/{repo}")
            
        except Exception as e:
            logger.error(f"Error fetching repository via API: {e}")
            raise
        
        return results
    
    def _collect_via_clone(self, **kwargs) -> List[CollectedDocument]:
        """Collect documents by cloning repository (fallback method)."""
        results = []
        
        try:
            # Clean up existing tmp directory
            _rmtree_windows(self.tmp_dir)
            
            # Clone repository
            logger.info(f"Cloning repository: {self.repo_url}")
            Repo.clone_from(self.repo_url, self.tmp_dir, branch=self.branch, depth=1)
            
            # Walk through files
            for root, _, files in os.walk(self.tmp_dir):
                # Skip .git directory
                if '.git' in root:
                    continue
                
                for filename in files:
                    try:
                        ext = os.path.splitext(filename)[1].lower()
                        if ext not in self.ALLOWED_EXTENSIONS:
                            continue
                        
                        full_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(full_path, self.tmp_dir)
                        
                        # Use ParserFactory to parse content if available
                        try:
                            parser = ParserFactory.get_parser(full_path)
                            if parser:
                                parsed_doc = parser.parse(full_path)
                                content = parsed_doc.content
                            else:
                                # Fallback to simple text reading
                                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                                    content = f.read()
                        except Exception as parse_error:
                            logger.warning(f"Failed to parse {filename} with parser: {parse_error}. Falling back to text.")
                            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                        
                        if not content.strip():
                            continue
                            
                        # Extract chunk config if provided
                        chunk_config = kwargs.get("chunk_config", {})
                        
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
                                "file_size": len(content),
                                "chunk_config": chunk_config
                            }
                        )
                        results.append(doc)
                        
                    except Exception as e:
                        logger.warning(f"Error processing file {full_path}: {e}")
                        continue
                                  
            logger.info(f"GitHubAdapter collected {len(results)} documents from {self.repo_url}")
            
        except Exception as e:
            logger.error(f"Error cloning repository {self.repo_url}: {e}")
            raise
        
        finally:
            # Cleanup
            _rmtree_windows(self.tmp_dir)
        
        return results
    
    def collect(self, **kwargs) -> List[CollectedDocument]:
        """
        Collect documents from GitHub repository.
        Uses API by default, falls back to cloning if needed.
        
        Returns:
            List of CollectedDocument objects
        """
        if self.use_api:
            try:
                logger.info("Using GitHub API to fetch repository...")
                results = self._collect_via_api(**kwargs)
            except Exception as e:
                logger.warning(f"API fetch failed: {e}. Falling back to git clone...")
                self.use_api = False
                results = self._collect_via_clone(**kwargs)
        else:
            logger.info("Using git clone to fetch repository...")
            results = self._collect_via_clone(**kwargs)
        
        return results

