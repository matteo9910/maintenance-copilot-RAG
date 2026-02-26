"""
Cohere Reranker via Azure AI.

Integrates Cohere Rerank v4.0 Pro hosted on Azure for
improving retrieval quality by reranking candidate documents.
"""
import httpx
from typing import List, Optional
from langchain_core.documents import Document

from app.core.config import settings


def rerank_documents(
    query: str,
    documents: List[Document],
    top_n: int = 4,
) -> List[Document]:
    """
    Rerank documents using Cohere Rerank v4.0 Pro via Azure.

    Args:
        query: The search query to rerank against.
        documents: List of candidate documents from initial retrieval.
        top_n: Number of top documents to return after reranking.

    Returns:
        Reranked list of documents (top_n best matches).
    """
    if not documents:
        return documents

    if not is_reranker_available():
        print("Reranker not available, returning documents as-is")
        return documents[:top_n]

    try:
        doc_texts = [doc.page_content for doc in documents]

        payload = {
            "model": settings.AZURE_RERANKER_MODEL,
            "query": query,
            "documents": doc_texts,
            "top_n": min(top_n, len(documents)),
        }

        with httpx.Client(verify=False, timeout=30.0) as client:
            response = client.post(
                settings.AZURE_RERANKER_ENDPOINT,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "api-key": settings.AZURE_RERANKER_API_KEY,
                },
            )
            response.raise_for_status()
            result = response.json()

        reranked_docs = []
        for item in result.get("results", []):
            idx = item.get("index", 0)
            score = item.get("relevance_score", 0.0)
            if idx < len(documents):
                doc = documents[idx]
                doc.metadata["rerank_score"] = score
                reranked_docs.append(doc)

        print(f"Reranker: {len(documents)} candidates -> {len(reranked_docs)} reranked")
        return reranked_docs

    except Exception as e:
        print(f"Reranker error: {e}, returning original documents")
        return documents[:top_n]


def is_reranker_available() -> bool:
    """Check if the Cohere reranker is configured."""
    return bool(
        settings.AZURE_RERANKER_ENDPOINT
        and settings.AZURE_RERANKER_API_KEY
    )
