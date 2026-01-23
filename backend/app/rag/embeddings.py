"""OpenAI Embeddings Configuration."""
import httpx
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI
from app.core.config import settings


def get_embeddings() -> OpenAIEmbeddings:
    """Get OpenAI embeddings instance with SSL handling for corporate networks."""
    # Create custom http client that handles corporate SSL certificates
    http_client = httpx.Client(verify=False)

    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
        http_client=http_client
    )
