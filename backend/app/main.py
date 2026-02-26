"""
FastAPI Entry Point - Maintenance RAG PoC
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api import chat, documents
from app.rag.vector_store import get_collection_stats
from app.rag.llm import get_available_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    print("Starting Maintenance RAG API...")
    stats = get_collection_stats()
    print(f"Vector Store: {stats['count']} documents indexed")
    yield
    # Shutdown
    print("Shutting down Maintenance RAG API...")


app = FastAPI(
    title="Maintenance RAG API",
    description="API for Industrial Maintenance RAG PoC",
    version="0.1.0",
    lifespan=lifespan
)

# CORS Configuration - Allow frontend and common development origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])

# Serve PDF files from raw_pdfs directory
PDF_DIRECTORY = Path(__file__).parent.parent.parent / "data" / "raw_pdfs"

# Serve extracted images from data/images directory
IMAGES_DIRECTORY = Path(__file__).parent.parent.parent / "data" / "images"

@app.get("/api/pdfs/{filename}")
async def serve_pdf(filename: str):
    """Serve PDF files from the raw_pdfs directory."""
    pdf_path = PDF_DIRECTORY / filename
    if pdf_path.exists() and pdf_path.suffix.lower() == ".pdf":
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=filename
        )
    return {"error": "PDF not found"}


@app.get("/api/images/{pdf_name}/{image_file}")
async def serve_image(pdf_name: str, image_file: str):
    """Serve extracted images from the images directory."""
    image_path = IMAGES_DIRECTORY / pdf_name / image_file
    if not image_path.exists():
        return {"error": "Image not found"}

    # Determine media type from extension
    ext = image_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
    }
    media_type = media_types.get(ext, "image/png")

    return FileResponse(
        path=image_path,
        media_type=media_type,
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"status": "ok", "message": "Maintenance RAG API is running"}


@app.get("/api/health")
async def health_check():
    """Detailed health check endpoint."""
    try:
        stats = get_collection_stats()
        vector_store_status = "ok" if stats.get("status") == "ok" else "error"
        vector_count = stats.get("count", 0)
    except Exception:
        vector_store_status = "error"
        vector_count = 0

    return {
        "status": "healthy",
        "version": "0.1.0",
        "components": {
            "api": "ok",
            "vector_store": {
                "status": vector_store_status,
                "documents_indexed": vector_count
            },
            "llm_provider": "azure_openai"
        },
        "available_models": list(get_available_models().keys())
    }


@app.get("/api/models")
async def get_models():
    """Get available LLM models."""
    models = get_available_models()
    return {
        "models": [
            {"id": model_id, "name": name}
            for model_id, name in models.items()
        ],
        "default": settings.DEFAULT_MODEL
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
