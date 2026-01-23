"""Chat API Endpoint."""
import uuid
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rag.chain import query_rag
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
    """Source document reference."""
    content: str
    source: str
    page: Optional[int] = None


class ChatResponse(BaseModel):
    """Chat response schema."""
    answer: str
    sources: List[SourceDocument]
    conversation_id: str
    model_used: str


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

        # Format sources
        sources = [
            SourceDocument(
                content=src.get("content", ""),
                source=src.get("source", "Unknown"),
                page=src.get("page")
            )
            for src in result.get("sources", [])
        ]

        return ChatResponse(
            answer=result["answer"],
            sources=sources,
            conversation_id=str(uuid.uuid4()),
            model_used=request.model or "openai/gpt-4o"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.get("/models")
async def get_models():
    """Get list of available LLM models."""
    return {"models": get_available_models()}
