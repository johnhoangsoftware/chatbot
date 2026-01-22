# ingest_service/adapters/url_adapter.py
"""
Adapter for collecting data from web URLs.
Supports general web pages, with content extraction.
"""
import re
import uuid
from typing import List, Optional
from urllib.parse import urlparse
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from .base import BaseAdapter, CollectedDocument
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class URLAdapter(BaseAdapter):
    """
    Adapter for collecting documents from web URLs.
    Extracts text content from HTML pages.
    """
    
    REQUEST_TIMEOUT = 30
    MAX_CONTENT_SIZE_MB = 50
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    def __init__(self, url: str = None, urls: List[str] = None):
        """
        Initialize with single URL or list of URLs.
        
        Args:
            url: Single URL
            urls: List of URLs
        """
        self.urls = []
        if url:
            self.urls.append(url)
        if urls:
            self.urls.extend(urls)
    
    @property
    def source_type(self) -> str:
        return "url"
    
    def validate(self, url: str = None, **kwargs) -> bool:
        """Validate that URLs are accessible."""
        urls = [url] if url else self.urls
        
        for u in urls:
            if not self._is_valid_url(u):
                return False
        return True
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid format."""
        try:
            result = urlparse(url)
            return all([result.scheme in ('http', 'https'), result.netloc])
        except:
            return False
    
    def _get_headers(self) -> dict:
        """Get request headers."""
        return {
            'User-Agent': self.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    
    def collect(self, url: str = None, **kwargs) -> List[CollectedDocument]:
        """
        Collect documents from URLs.
        
        Args:
            url: Optional single URL to process (overrides constructor URLs)
            
        Returns:
            List of CollectedDocument objects
        """
        urls = [url] if url else self.urls
        results = []
        
        for u in urls:
            try:
                doc = self._collect_single_url(u)
                if doc:
                    results.append(doc)
            except Exception as e:
                logger.error(f"Error collecting URL {u}: {e}")
                continue
        
        logger.info(f"URLAdapter collected {len(results)} documents")
        return results
    
    def _collect_single_url(self, url: str) -> Optional[CollectedDocument]:
        """Collect content from a single URL."""
        if not self._is_valid_url(url):
            logger.error(f"Invalid URL: {url}")
            return None
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Check content size
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > self.MAX_CONTENT_SIZE_MB:
                    logger.error(f"Content too large: {size_mb}MB")
                    return None
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = soup.title.string if soup.title else url
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            # Find main content
            main_content = (
                soup.find('main') or
                soup.find('article') or
                soup.find('div', class_='content') or
                soup.find('div', id='content') or
                soup.body
            )
            
            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
            else:
                text = soup.get_text(separator='\n', strip=True)
            
            # Clean up text
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = text.strip()
            
            if not text:
                logger.warning(f"No content extracted from {url}")
                return None
            
            # Create CollectedDocument
            parsed = urlparse(url)
            return CollectedDocument(
                raw_id=self.generate_raw_id(),
                content=text,
                source_type=self.source_type,
                source_path=url,
                source_name=title[:100] if title else parsed.netloc,
                metadata={
                    "url": url,
                    "final_url": response.url,
                    "domain": parsed.netloc,
                    "title": title,
                    "content_length": len(text),
                    "status_code": response.status_code
                }
            )
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return None
