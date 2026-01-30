import logging
import os
import sys
import io
from datetime import datetime
from functools import lru_cache


def safe_log_message(message: str) -> str:
    """Make log message safe for Windows console."""
    try:
        # Try to encode with cp1252
        message.encode('cp1252')
        return message
    except UnicodeEncodeError:
        # Replace problematic characters with '?'
        return message.encode('ascii', errors='replace').decode('ascii')


def setup_logger(name: str, log_level: int = logging.INFO) -> logging.Logger:
    """Setup and configure a logger instance with UTF-8 encoding."""
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Console handler with UTF-8 encoding for Windows
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Force UTF-8 encoding for Windows
    if sys.platform == 'win32':
        console_handler.stream = io.TextIOWrapper(
            sys.stdout.buffer, 
            encoding='utf-8',
            errors='replace'  # Replace unencodable characters
        )
    
    console_handler.setLevel(log_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    
    # File handler for logs (always UTF-8)
    file_handler = logging.FileHandler(
        f"logs/app_{datetime.now().strftime('%Y%m%d')}.log",
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_format)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


class RetrievalLogger:
    """Dedicated logger for RAG retrieval operations."""
    
    def __init__(self):
        self.logger = setup_logger("retrieval", logging.DEBUG)
        
        # Separate file for retrieval logs (UTF-8)
        retrieval_handler = logging.FileHandler(
            f"logs/retrieval_{datetime.now().strftime('%Y%m%d')}.log",
            encoding='utf-8'
        )
        retrieval_handler.setLevel(logging.DEBUG)
        retrieval_format = logging.Formatter(
            '%(asctime)s - RETRIEVAL - %(message)s'
        )
        retrieval_handler.setFormatter(retrieval_format)
        self.logger.addHandler(retrieval_handler)
    
    def log_query(self, query: str, user_id: str = "anonymous"):
        """Log incoming query with safe encoding."""
        safe_query = safe_log_message(query)
        safe_user = safe_log_message(user_id)
        self.logger.info(f"QUERY | user={safe_user} | query={safe_query}")
    
    def log_retrieved_chunks(self, query: str, chunks: list, scores: list = None):
        """Log retrieved chunks for debugging."""
        safe_query = safe_log_message(query)
        self.logger.debug(f"RETRIEVAL | query={safe_query}")
        
        for i, chunk in enumerate(chunks):
            score = scores[i] if scores else "N/A"
            content_preview = chunk[:200].replace('\n', ' ') if isinstance(chunk, str) else str(chunk)[:200]
            safe_content = safe_log_message(content_preview)
            self.logger.debug(f"  CHUNK {i+1} | score={score} | content={safe_content}...")
    
    def log_response(self, query: str, response: str, source_docs: list = None):
        """Log generated response."""
        safe_query = safe_log_message(query[:100])
        self.logger.info(f"RESPONSE | query={safe_query}... | response_length={len(response)}")
        
        if source_docs:
            self.logger.debug(f"  SOURCES | count={len(source_docs)}")


@lru_cache()
def get_retrieval_logger() -> RetrievalLogger:
    """Get cached retrieval logger instance."""
    return RetrievalLogger()
