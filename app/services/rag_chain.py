from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from app.config import get_settings
from app.services.vector_store import get_vector_store
from app.services.domain_dictionary import get_domain_dictionary
from app.utils.logger import setup_logger, get_retrieval_logger

logger = setup_logger(__name__)
retrieval_logger = get_retrieval_logger()


# System prompt for automotive domain
SYSTEM_PROMPT = """You are an expert automotive domain assistant specializing in:
- ASPICE (Automotive SPICE) - Software process improvement
- AUTOSAR - Automotive software architecture
- ISO 26262 - Functional safety standards

Your role is to help users understand automotive documentation, answer technical questions, 
and provide insights based on the uploaded documents.

Guidelines:
1. Answer based on the provided context from documents when available
2. Use precise automotive terminology
3. If information is not in the context, clearly state that
4. Provide references to specific document sections when possible
5. For safety-related topics (ISO 26262), be extra careful and precise

{domain_context}

Context from documents:
{context}

Previous conversation:
{chat_history}

User question: {question}

Please provide a helpful and accurate response:"""


class RAGChain:
    """RAG chain for automotive document Q&A."""
    
    def __init__(self):
        settings = get_settings()
        
        # Initialize primary LLM (Gemini)
        self.llm = None
        self.backup_llm = None
        model_name = "gemini-2.5-flash"
        
        if settings.google_api_key:
            logger.info(f"🔧 DEBUG: Initializing Gemini with model: {model_name}")
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=settings.google_api_key,
                temperature=0.3,
            )
            logger.info(f"✓ DEBUG: Gemini model initialized successfully")
        else:
            logger.warning("⚠ DEBUG: No Google API key found")
        
        # Initialize backup LLM (OpenAI-compatible)
        if settings.backup_llm_enabled and settings.backup_llm_api_key:
            try:
                from langchain_openai import ChatOpenAI
                self.backup_llm = ChatOpenAI(
                    model=settings.backup_llm_model,
                    api_key=settings.backup_llm_api_key,
                    base_url=settings.backup_llm_base_url,
                    temperature=0.3,
                )
                logger.info(f"✓ Backup LLM initialized: {settings.backup_llm_base_url}")
            except Exception as e:
                logger.warning(f"⚠ Failed to initialize backup LLM: {e}")
        
        # Initialize vector store and domain dictionary
        self.vector_store = get_vector_store()
        self.domain_dict = get_domain_dictionary()
        
        # Simple conversation history per session
        self.sessions: Dict[str, List[Dict[str, str]]] = {}
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT)
        
        logger.info("RAGChain initialized")
    
    def _get_chat_history(self, session_id: str) -> str:
        """Get formatted chat history for a session."""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        history = self.sessions[session_id]
        if not history:
            return "No previous conversation."
        
        formatted = []
        for entry in history[-5:]:  # Keep last 5 exchanges
            formatted.append(f"User: {entry['question']}")
            formatted.append(f"Assistant: {entry['answer'][:200]}...")
        
        return "\n".join(formatted)
    
    def _save_to_history(self, session_id: str, question: str, answer: str):
        """Save Q&A to session history."""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        self.sessions[session_id].append({
            "question": question,
            "answer": answer
        })
        
        # Keep only last 10 entries
        if len(self.sessions[session_id]) > 10:
            self.sessions[session_id] = self.sessions[session_id][-10:]
    
    def query(
        self, 
        question: str, 
        session_id: str = "default",
        k: int = 5,
        filter_document: str = None
    ) -> Dict[str, Any]:
        """
        Query the RAG system with a question.
        
        Args:
            question: User's question
            session_id: Session ID for conversation history
            k: Number of documents to retrieve
            filter_document: Optional document ID to filter results
            
        Returns:
            Dict with answer, sources, and metadata
        """
        if not self.llm:
            return {
                "answer": "Error: LLM not configured. Please set GOOGLE_API_KEY in .env file.",
                "sources": [],
                "error": True
            }
        
        # Log the query
        retrieval_logger.log_query(question, session_id)
        
        # Get domain context for the query
        domain_context = self.domain_dict.get_context_for_query(question)
        
        # Search vector store
        filter_meta = {"document_id": filter_document} if filter_document else None
        search_results = self.vector_store.search(question, k=k, filter_metadata=filter_meta)
        
        # Log retrieved chunks
        chunks = [r["content"] for r in search_results]
        scores = [r.get("score", 0) for r in search_results]
        retrieval_logger.log_retrieved_chunks(question, chunks, scores)
        
        # Format context
        context = self._format_context(search_results)
        
        # Get conversation history
        chat_history = self._get_chat_history(session_id)
        
        # Generate response
        try:
            formatted_prompt = self.prompt.format_messages(
                domain_context=domain_context,
                context=context,
                chat_history=chat_history,
                question=question
            )
            
            # Try primary LLM first
            answer = None
            try:
                if self.llm:
                    response = self.llm.invoke(formatted_prompt)
                    answer = response.content
                    logger.info("✓ Primary LLM (Gemini) responded successfully")
            except Exception as primary_error:
                logger.warning(f"⚠ Primary LLM failed: {primary_error}")
                
                # Fallback to backup LLM
                if self.backup_llm:
                    logger.info("🔄 Trying backup LLM...")
                    try:
                        response = self.backup_llm.invoke(formatted_prompt)
                        answer = response.content
                        logger.info("✓ Backup LLM responded successfully")
                    except Exception as backup_error:
                        logger.error(f"✗ Backup LLM also failed: {backup_error}")
                        raise backup_error
                else:
                    raise primary_error
            
            if not answer:
                raise Exception("No LLM available")
            
            # Save to history
            self._save_to_history(session_id, question, answer)
            
            # Log response
            retrieval_logger.log_response(question, answer, search_results)
            
            # Format sources
            sources = self._format_sources(search_results)
            
            return {
                "answer": answer,
                "sources": sources,
                "domain_terms_used": bool(domain_context),
                "chunks_retrieved": len(search_results)
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "answer": f"Error generating response: {str(e)}",
                "sources": [],
                "error": True
            }
    
    async def query_stream(
        self, 
        question: str, 
        session_id: str = "default",
        k: int = 5,
        filter_document: str = None
    ):
        """
        Query with streaming response - yields tokens as they are generated.
        """
        if not self.llm:
            yield "Error: LLM not configured. Please set GOOGLE_API_KEY."
            return
        
        # Get domain context
        domain_context = self.domain_dict.get_context_for_query(question)
        
        # Search vector store
        filter_meta = {"document_id": filter_document} if filter_document else None
        search_results = self.vector_store.search(question, k=k, filter_metadata=filter_meta)
        
        # Format context
        context = self._format_context(search_results)
        chat_history = self._get_chat_history(session_id)
        
        # Format prompt
        formatted_prompt = self.prompt.format_messages(
            domain_context=domain_context,
            context=context,
            chat_history=chat_history,
            question=question
        )
        
        # Stream response
        full_response = ""
        try:
            async for chunk in self.llm.astream(formatted_prompt):
                if chunk.content:
                    full_response += chunk.content
                    yield chunk.content
            
            # Save to history after complete
            self._save_to_history(session_id, question, full_response)
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"\n\nError: {str(e)}"
    
    def _format_context(self, search_results: List[Dict]) -> str:
        """Format search results into context string."""
        if not search_results:
            return "No relevant documents found."
        
        context_parts = []
        for i, result in enumerate(search_results, 1):
            content = result["content"]
            metadata = result.get("metadata", {})
            source = metadata.get("filename", "Unknown")
            chunk_idx = metadata.get("chunk_index", "?")
            
            context_parts.append(
                f"[Source {i}: {source}, Chunk {chunk_idx}]\n{content}"
            )
        
        return "\n\n---\n\n".join(context_parts)
    
    def _format_sources(self, search_results: List[Dict]) -> List[Dict]:
        """Format sources for response."""
        sources = []
        seen = set()
        
        for result in search_results:
            metadata = result.get("metadata", {})
            doc_id = metadata.get("document_id", "unknown")
            filename = metadata.get("filename", "Unknown")
            
            if doc_id not in seen:
                seen.add(doc_id)
                sources.append({
                    "document_id": doc_id,
                    "filename": filename,
                    "relevance_score": result.get("score", 0)
                })
        
        return sources
    
    def clear_session(self, session_id: str):
        """Clear conversation history for a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleared session: {session_id}")


# Singleton instance
_rag_chain_instance: Optional[RAGChain] = None


def get_rag_chain() -> RAGChain:
    """Get or create RAG chain instance."""
    global _rag_chain_instance
    if _rag_chain_instance is None:
        _rag_chain_instance = RAGChain()
    return _rag_chain_instance
