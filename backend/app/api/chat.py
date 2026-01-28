"""Chat API Endpoint with Streaming Support."""
import uuid
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.rag.chain import query_rag, query_rag_stream
from app.rag.llm import get_available_models

router = APIRouter()


class MessageHistory(BaseModel):
    """Single message in chat history."""
    role: str = Field(..., description="Either 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request schema."""
    query: str = Field(..., min_length=1, description="User's question")
    model: Optional[str] = Field(None, description="Model ID to use (e.g., 'openai/gpt-4o')")
    history: Optional[List[MessageHistory]] = Field(default=[], description="Conversation history")
    image: Optional[str] = Field(None, description="Base64 encoded image (optional)")


class SourceDocument(BaseModel):
    """Source document reference with full metadata for trust layer."""
    content: str  # Extended content preview (1000-1500 chars) for trust layer
    source: str
    page: Optional[int] = None
    chapter: Optional[str] = None
    section: Optional[str] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    relevance_score: Optional[float] = None


class RAGMetadata(BaseModel):
    """Metadata about RAG processing."""
    mode: str = Field(default="legacy", description="RAG mode: 'agentic' or 'legacy'")
    iterations: int = Field(default=1, description="Number of retrieval iterations")
    queries_executed: List[str] = Field(default=[], description="Search queries executed")


class ChatResponse(BaseModel):
    """Chat response schema."""
    answer: str
    sources: List[SourceDocument]
    conversation_id: str
    model_used: str
    rag_metadata: Optional[RAGMetadata] = Field(None, description="RAG processing metadata")


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for RAG queries.

    Receives a question, retrieves relevant documents from ChromaDB,
    and generates an answer using the selected LLM via OpenRouter.
    """
    try:
        # Convert history to expected format
        history = [{"role": msg.role, "content": msg.content} for msg in (request.history or [])]

        # Query RAG system
        result = await query_rag(
            question=request.query,
            model_id=request.model,
            chat_history=history
        )

        # Format sources with extended metadata for trust layer
        sources = [
            SourceDocument(
                content=src.get("content", ""),
                source=src.get("source", "Unknown"),
                page=src.get("page"),
                chapter=src.get("chapter"),
                section=src.get("section"),
                chunk_index=src.get("chunk_index"),
                total_chunks=src.get("total_chunks"),
                relevance_score=src.get("relevance_score")
            )
            for src in result.get("sources", [])
        ]

        # Extract RAG metadata if available
        metadata = result.get("metadata", {})
        rag_metadata = RAGMetadata(
            mode=metadata.get("mode", "legacy"),
            iterations=metadata.get("iterations", 1),
            queries_executed=metadata.get("queries_executed", [])
        )

        return ChatResponse(
            answer=result["answer"],
            sources=sources,
            conversation_id=str(uuid.uuid4()),
            model_used=request.model or "openai/gpt-4o",
            rag_metadata=rag_metadata
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.get("/models")
async def get_models():
    """Get list of available LLM models."""
    return {"models": get_available_models()}


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint for reduced latency.

    Returns a Server-Sent Events (SSE) stream with:
    - event: token - Each generated token
    - event: sources - Source documents (at the end)
    - event: metadata - RAG processing metadata (at the end)
    - event: done - Stream completion signal

    This endpoint allows the frontend to display the response
    as it's being generated, significantly improving perceived latency.
    """
    try:
        # Convert history to expected format
        history = [{"role": msg.role, "content": msg.content} for msg in (request.history or [])]

        # Create streaming generator
        async def generate():
            async for chunk in query_rag_stream(
                question=request.query,
                model_id=request.model,
                chat_history=history
            ):
                yield chunk

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing streaming query: {str(e)}")
