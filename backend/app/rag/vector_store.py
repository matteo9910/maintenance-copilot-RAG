"""ChromaDB Vector Store Management."""
import os
from pathlib import Path
from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.core.config import settings
from app.rag.embeddings import get_embeddings

# Global client instance to avoid conflicts
_chroma_client = None


def get_chroma_client() -> chromadb.PersistentClient:
    """Get ChromaDB persistent client (singleton)."""
    global _chroma_client
    if _chroma_client is None:
        persist_dir = Path(settings.CHROMA_PERSIST_DIRECTORY)
        persist_dir.mkdir(parents=True, exist_ok=True)

        _chroma_client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False)
        )
    return _chroma_client


def get_vector_store() -> Chroma:
    """Get LangChain Chroma vector store instance."""
    client = get_chroma_client()

    return Chroma(
        client=client,
        collection_name=settings.CHROMA_COLLECTION_NAME,
        embedding_function=get_embeddings()
    )


def get_retriever(k: int = 4):
    """Get retriever from vector store."""
    vector_store = get_vector_store()
    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k}
    )


def add_documents(documents: list[Document]) -> int:
    """Add documents to vector store. Returns number of documents added."""
    if not documents:
        return 0

    vector_store = get_vector_store()
    vector_store.add_documents(documents)
    return len(documents)


def get_collection_stats() -> dict:
    """Get statistics about the vector store collection."""
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(settings.CHROMA_COLLECTION_NAME)
        return {
            "name": settings.CHROMA_COLLECTION_NAME,
            "count": collection.count(),
            "status": "ok"
        }
    except Exception as e:
        return {
            "name": settings.CHROMA_COLLECTION_NAME,
            "count": 0,
            "status": f"error: {str(e)}"
        }


def clear_collection() -> bool:
    """Clear all documents from the collection."""
    global _chroma_client
    try:
        client = get_chroma_client()
        try:
            client.delete_collection(settings.CHROMA_COLLECTION_NAME)
        except ValueError:
            # Collection doesn't exist, that's fine
            pass
        return True
    except Exception:
        return False
