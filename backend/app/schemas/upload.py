"""Upload schemas for document ingestion."""
from pydantic import BaseModel, Field
from typing import List


class UploadResponse(BaseModel):
    """Response schema for file upload."""
    success: bool
    filename: str
    message: str
    chunks_created: int = Field(0, description="Number of chunks created from document")


class BatchUploadResponse(BaseModel):
    """Response schema for batch upload."""
    total_files: int
    successful: int
    failed: int
    results: List[UploadResponse]
