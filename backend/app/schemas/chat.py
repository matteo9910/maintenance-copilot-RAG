"""Chat schemas for RAG interactions."""
from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""
    message: str = Field(..., min_length=1, description="User's question")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for context")


class SourceDocument(BaseModel):
    """Schema for source documents used in response."""
    content: str
    source: str
    page: Optional[int] = None
    relevance_score: Optional[float] = None


class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""
    answer: str = Field(..., description="AI-generated answer")
    sources: List[SourceDocument] = Field(default_factory=list, description="Source documents used")
    conversation_id: str = Field(..., description="Conversation ID for follow-up")
