"""
OpenAI-Compatible API for OpenWebUI integration.
Exposes RAG functionality through OpenAI chat/completions format.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import time
import uuid

from app.services.rag_chain import get_rag_chain
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/v1", tags=["openai-compatible"])


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "rag-model"
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    stream: Optional[bool] = False


class ChatCompletionChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]


@router.get("/models")
async def list_models():
    """List available models - required for OpenWebUI."""
    return {
        "object": "list",
        "data": [
            {
                "id": "rag-model",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local",
                "name": "Document RAG Model"
            }
        ]
    }


@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint.
    Works with OpenWebUI, LangChain, and other OpenAI-compatible clients.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages cannot be empty")
    
    # Get the last user message
    user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break
    
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")
    
    logger.info(f"OpenAI-compatible request: model={request.model}, message={user_message[:50]}...")
    
    rag_chain = get_rag_chain()
    
    if request.stream:
        # Streaming response
        async def generate():
            request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            
            async for token in rag_chain.query_stream(
                question=user_message,
                session_id="openwebui"
            ):
                # SSE format for OpenAI streaming
                chunk = {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": token},
                        "finish_reason": None
                    }]
                }
                yield f"data: {__import__('json').dumps(chunk)}\n\n"
            
            # Send final chunk
            final_chunk = {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {__import__('json').dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
    else:
        # Non-streaming response
        result = rag_chain.query(
            question=user_message,
            session_id="openwebui"
        )
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=Message(role="assistant", content=result["answer"]),
                    finish_reason="stop"
                )
            ]
        )
