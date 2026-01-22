from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.config import init_directories, get_settings
from app.routers import upload, chat, compare
from app.utils.logger import setup_logger

# Initialize directories and logger
init_directories()
logger = setup_logger(__name__)

app = FastAPI(
    title="Automotive Chatbot POC",
    description="RAG-based chatbot for automotive domain documents",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(compare.router, prefix="/api", tags=["compare"])

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    """Serve the main UI."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Automotive Chatbot POC API"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "environment": settings.app_env,
        "api_configured": bool(settings.google_api_key)
    }


@app.get("/debug/config")
async def debug_config():
    """Debug endpoint to check current configuration."""
    from app.services.rag_chain import get_rag_chain
    settings = get_settings()
    rag = get_rag_chain()
    
    return {
        "google_api_key_set": bool(settings.google_api_key),
        "google_api_key_prefix": settings.google_api_key[:10] + "..." if settings.google_api_key else None,
        "llm_initialized": rag.llm is not None,
        "llm_model": rag.llm.model_name if rag.llm else None,
        "embedding_provider": settings.embedding_provider,
        "environment": settings.app_env,
        "debug_mode": settings.debug
    }


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Automotive Chatbot POC...")
    settings = get_settings()
    if not settings.google_api_key:
        logger.warning("GOOGLE_API_KEY not configured. Please set it in .env file.")
    logger.info("Application started successfully.")
