"""Documents API Endpoint."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.rag.ingestion import get_indexed_documents, ingest_pdfs
from app.rag.vector_store import get_collection_stats, clear_collection

router = APIRouter()


class DocumentInfo(BaseModel):
    """Information about an indexed document."""
    filename: str
    machine: str
    doc_type: str
    chunk_count: int


class DocumentsResponse(BaseModel):
    """Response for documents list endpoint."""
    documents: List[DocumentInfo]
    total_chunks: int


class IngestRequest(BaseModel):
    """Request for ingestion endpoint."""
    clear_existing: Optional[bool] = False


class IngestResponse(BaseModel):
    """Response for ingestion endpoint."""
    success: bool
    message: str
    files_processed: int
    chunks_created: int
    total_documents_in_db: int


@router.get("", response_model=DocumentsResponse)
async def list_documents():
    """List all indexed documents in the knowledge base."""
    try:
        documents = get_indexed_documents()
        stats = get_collection_stats()

        doc_list = [
            DocumentInfo(
                filename=doc["filename"],
                machine=doc["machine"],
                doc_type=doc["doc_type"],
                chunk_count=doc["chunk_count"]
            )
            for doc in documents
        ]

        return DocumentsResponse(
            documents=doc_list,
            total_chunks=stats.get("count", 0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")


@router.post("/ingest", response_model=IngestResponse)
async def trigger_ingestion(request: IngestRequest = IngestRequest()):
    """
    Trigger ingestion of PDFs from the raw_pdfs directory.

    This endpoint reads all PDF files from data/raw_pdfs,
    processes them into chunks, and stores them in ChromaDB.
    """
    try:
        result = ingest_pdfs(clear_existing=request.clear_existing)

        if result["success"]:
            return IngestResponse(
                success=True,
                message=f"Successfully processed {result['files_processed']} files",
                files_processed=result["files_processed"],
                chunks_created=result["chunks_created"],
                total_documents_in_db=result["total_documents_in_db"]
            )
        else:
            return IngestResponse(
                success=False,
                message=result.get("error", "Unknown error"),
                files_processed=0,
                chunks_created=0,
                total_documents_in_db=0
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during ingestion: {str(e)}")


@router.delete("/clear")
async def clear_documents():
    """Clear all documents from the knowledge base."""
    try:
        success = clear_collection()
        if success:
            return {"success": True, "message": "Knowledge base cleared"}
        else:
            return {"success": False, "message": "Failed to clear knowledge base"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing documents: {str(e)}")


@router.get("/stats")
async def get_stats():
    """Get statistics about the knowledge base."""
    try:
        stats = get_collection_stats()
        return {
            "collection_name": stats.get("name"),
            "total_chunks": stats.get("count", 0),
            "status": stats.get("status")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")
