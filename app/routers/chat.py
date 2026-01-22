from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from app.services.rag_chain import get_rag_chain
from app.services.domain_dictionary import get_domain_dictionary
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    session_id: Optional[str] = "default"
    document_id: Optional[str] = None  # Filter to specific document
    k: Optional[int] = 5  # Number of chunks to retrieve


class SourceInfo(BaseModel):
    """Source document information."""
    document_id: str
    filename: str
    relevance_score: float


class ChatResponse(BaseModel):
    """Chat response model."""
    answer: str
    sources: List[SourceInfo]
    domain_terms_used: bool
    chunks_retrieved: int


class TermLookupResponse(BaseModel):
    """Term lookup response."""
    term: str
    definition: str
    domain: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the RAG system.
    
    - Retrieves relevant document chunks
    - Augments with domain dictionary terms
    - Generates response using Gemini AI
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    logger.info(f"Chat request: session={request.session_id}, message={request.message[:50]}...")
    
    try:
        rag_chain = get_rag_chain()
        
        result = rag_chain.query(
            question=request.message,
            session_id=request.session_id,
            k=request.k,
            filter_document=request.document_id
        )
        
        if result.get("error"):
            raise HTTPException(status_code=500, detail=result["answer"])
        
        # Format sources
        sources = [
            SourceInfo(
                document_id=s["document_id"],
                filename=s["filename"],
                relevance_score=round(s["relevance_score"], 3)
            )
            for s in result.get("sources", [])
        ]
        
        return ChatResponse(
            answer=result["answer"],
            sources=sources,
            domain_terms_used=result.get("domain_terms_used", False),
            chunks_retrieved=result.get("chunks_retrieved", 0)
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/clear/{session_id}")
async def clear_session(session_id: str):
    """Clear conversation history for a session."""
    rag_chain = get_rag_chain()
    rag_chain.clear_session(session_id)
    return {"success": True, "message": f"Session {session_id} cleared"}


@router.get("/terms/lookup/{term}")
async def lookup_term(term: str):
    """Look up an automotive term in the domain dictionary."""
    domain_dict = get_domain_dictionary()
    result = domain_dict.lookup(term)
    
    if result is None:
        raise HTTPException(status_code=404, detail=f"Term '{term}' not found")
    
    if "matches" in result:
        return {"matches": result["matches"]}
    
    return TermLookupResponse(
        term=result["term"],
        definition=result["definition"],
        domain=result["domain"]
    )


@router.get("/terms/search")
async def search_terms(q: str):
    """Search for automotive terms."""
    domain_dict = get_domain_dictionary()
    results = domain_dict.search(q)
    return {"results": results, "count": len(results)}


@router.get("/terms/domains")
async def list_domains():
    """List available domain dictionaries."""
    domain_dict = get_domain_dictionary()
    domains = []
    
    for domain, terms in domain_dict.dictionaries.items():
        domains.append({
            "name": domain,
            "term_count": len(terms)
        })
    
    return {"domains": domains}
