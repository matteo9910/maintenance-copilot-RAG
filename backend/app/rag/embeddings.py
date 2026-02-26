"""Azure OpenAI Embeddings Configuration."""
import httpx
from langchain_openai import AzureOpenAIEmbeddings
from app.core.config import settings


def get_embeddings() -> AzureOpenAIEmbeddings:
    """Get Azure OpenAI embeddings instance with SSL handling for corporate networks."""
    http_client = httpx.Client(verify=False)

    return AzureOpenAIEmbeddings(
        azure_deployment=settings.AZURE_EMBEDDING_DEPLOYMENT,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_EMBEDDING_API_VERSION,
        http_client=http_client,
    )