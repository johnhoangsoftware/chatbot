import logging
import os
from datetime import datetime
from functools import lru_cache


def setup_logger(name: str, log_level: int = logging.INFO) -> logging.Logger:
    """Setup and configure a logger instance."""
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    
    # File handler for retrieval logs
    file_handler = logging.FileHandler(
        f"logs/app_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setLevel(log_level)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_format)
    
    # Add handlers if not already added
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger


class RetrievalLogger:
    """Dedicated logger for RAG retrieval operations."""
    
    def __init__(self):
        self.logger = setup_logger("retrieval", logging.DEBUG)
        os.makedirs("logs", exist_ok=True)
        
        # Separate file for retrieval logs
        retrieval_handler = logging.FileHandler(
            f"logs/retrieval_{datetime.now().strftime('%Y%m%d')}.log"
        )
        retrieval_handler.setLevel(logging.DEBUG)
        retrieval_format = logging.Formatter(
            '%(asctime)s - RETRIEVAL - %(message)s'
        )
        retrieval_handler.setFormatter(retrieval_format)
        self.logger.addHandler(retrieval_handler)
    
    def log_query(self, query: str, user_id: str = "anonymous"):
        """Log incoming query."""
        self.logger.info(f"QUERY | user={user_id} | query={query}")
    
    def log_retrieved_chunks(self, query: str, chunks: list, scores: list = None):
        """Log retrieved chunks for debugging."""
        self.logger.debug(f"RETRIEVAL | query={query}")
        for i, chunk in enumerate(chunks):
            score = scores[i] if scores else "N/A"
            content_preview = chunk[:200].replace('\n', ' ') if isinstance(chunk, str) else str(chunk)[:200]
            self.logger.debug(f"  CHUNK {i+1} | score={score} | content={content_preview}...")
    
    def log_response(self, query: str, response: str, source_docs: list = None):
        """Log generated response."""
        self.logger.info(f"RESPONSE | query={query[:100]}... | response_length={len(response)}")
        if source_docs:
            self.logger.debug(f"  SOURCES | count={len(source_docs)}")


@lru_cache()
def get_retrieval_logger() -> RetrievalLogger:
    """Get cached retrieval logger instance."""
    return RetrievalLogger()
