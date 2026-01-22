from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.services.vector_store import get_vector_store
from app.services.rag_chain import get_rag_chain
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


class CompareRequest(BaseModel):
    """Document comparison request."""
    document_id_1: str
    document_id_2: str
    focus_area: Optional[str] = None  # Optional: what to focus comparison on


class Difference(BaseModel):
    """A single difference found."""
    category: str
    description: str
    document_1_content: Optional[str] = None
    document_2_content: Optional[str] = None


class CompareResponse(BaseModel):
    """Document comparison response."""
    summary: str
    differences: List[Difference]
    similarity_score: float
    documents_compared: List[str]


@router.post("/compare", response_model=CompareResponse)
async def compare_documents(request: CompareRequest):
    """
    Compare two documents and identify major differences.
    
    Uses RAG to:
    1. Retrieve content from both documents
    2. Analyze differences using LLM
    3. Return structured comparison
    """
    vector_store = get_vector_store()
    rag_chain = get_rag_chain()
    
    # Get chunks from both documents
    doc1_chunks = vector_store.get_documents_by_id(request.document_id_1)
    doc2_chunks = vector_store.get_documents_by_id(request.document_id_2)
    
    if not doc1_chunks:
        raise HTTPException(
            status_code=404, 
            detail=f"Document {request.document_id_1} not found"
        )
    
    if not doc2_chunks:
        raise HTTPException(
            status_code=404, 
            detail=f"Document {request.document_id_2} not found"
        )
    
    # Get document names
    doc1_name = doc1_chunks[0].get("metadata", {}).get("filename", "Document 1")
    doc2_name = doc2_chunks[0].get("metadata", {}).get("filename", "Document 2")
    
    # Prepare content for comparison
    doc1_content = "\n\n".join([c["content"] for c in doc1_chunks[:10]])  # Limit for API
    doc2_content = "\n\n".join([c["content"] for c in doc2_chunks[:10]])
    
    # Build comparison prompt
    focus_instruction = ""
    if request.focus_area:
        focus_instruction = f"\nFocus specifically on: {request.focus_area}"
    
    comparison_prompt = f"""Compare these two automotive documents and identify the major differences.
{focus_instruction}

=== DOCUMENT 1: {doc1_name} ===
{doc1_content[:5000]}

=== DOCUMENT 2: {doc2_name} ===
{doc2_content[:5000]}

Please provide:
1. A brief summary of the key differences (2-3 sentences)
2. A list of specific differences with categories (e.g., "Process", "Terminology", "Requirements", "Structure")
3. An estimated similarity score from 0.0 (completely different) to 1.0 (identical)

Format your response as:
SUMMARY: [your summary]
DIFFERENCES:
- [CATEGORY]: [description]
- [CATEGORY]: [description]
SIMILARITY: [0.0-1.0]"""

    try:
        # Use RAG chain's LLM directly for comparison
        if not rag_chain.llm:
            raise HTTPException(
                status_code=500, 
                detail="LLM not configured. Please set GOOGLE_API_KEY."
            )
        
        response = rag_chain.llm.invoke(comparison_prompt)
        response_text = response.content
        
        # Parse response
        summary, differences, similarity = _parse_comparison_response(response_text)
        
        logger.info(f"Compared documents: {doc1_name} vs {doc2_name}")
        
        return CompareResponse(
            summary=summary,
            differences=differences,
            similarity_score=similarity,
            documents_compared=[doc1_name, doc2_name]
        )
        
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _parse_comparison_response(response: str) -> tuple:
    """Parse LLM comparison response into structured data."""
    lines = response.strip().split('\n')
    
    summary = ""
    differences = []
    similarity = 0.5
    
    current_section = None
    
    for line in lines:
        line = line.strip()
        
        if line.startswith("SUMMARY:"):
            current_section = "summary"
            summary = line.replace("SUMMARY:", "").strip()
        elif line.startswith("DIFFERENCES:"):
            current_section = "differences"
        elif line.startswith("SIMILARITY:"):
            current_section = "similarity"
            try:
                sim_text = line.replace("SIMILARITY:", "").strip()
                similarity = float(sim_text)
                similarity = max(0.0, min(1.0, similarity))
            except:
                similarity = 0.5
        elif current_section == "summary" and line and not line.startswith("-"):
            summary += " " + line
        elif current_section == "differences" and line.startswith("-"):
            # Parse difference line: - [CATEGORY]: description
            diff_text = line[1:].strip()
            if ":" in diff_text:
                parts = diff_text.split(":", 1)
                category = parts[0].strip().strip("[]")
                description = parts[1].strip()
            else:
                category = "General"
                description = diff_text
            
            differences.append(Difference(
                category=category,
                description=description
            ))
    
    # Default if parsing failed
    if not summary:
        summary = "Comparison completed. See differences below."
    
    if not differences:
        differences.append(Difference(
            category="General",
            description="Documents have been compared. Review the full comparison for details."
        ))
    
    return summary.strip(), differences, similarity


@router.get("/compare/stats")
async def comparison_stats():
    """Get statistics about available documents for comparison."""
    vector_store = get_vector_store()
    stats = vector_store.get_collection_stats()
    
    return {
        "collection_name": stats["name"],
        "total_chunks": stats["count"],
        "comparison_available": stats["count"] > 0
    }
