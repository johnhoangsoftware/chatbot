from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    google_api_key: str = ""     
    backup_llm_enabled: bool = True
    backup_llm_base_url: str = "https://api.yescale.io/v1"
    backup_llm_api_key: str = ""
    backup_llm_model: str = "gpt-4o-2024-11-20"
    
    # Embedding Configuration
    # Options: "gemini" (online, rate limited) or "local" (offline, fast)
    embedding_provider: str = "local"
    embedding_model_name: str = "all-MiniLM-L6-v2"  # standard fast local model
    
    # App Settings
    app_env: str = "development"
    debug: bool = True
    
    # ChromaDB
    chroma_persist_dir: str = "./data/chroma_db"
    
    # Upload
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50
    
    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 100
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Create directories if they don't exist
def init_directories():
    """Initialize required directories."""
    settings = get_settings()
    directories = [
        settings.chroma_persist_dir,
        settings.upload_dir,
        "./logs",
        "./domain_data"
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
