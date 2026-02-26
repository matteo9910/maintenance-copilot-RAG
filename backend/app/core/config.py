"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""

    # Azure Model Deployments
    AZURE_GPT52_DEPLOYMENT: str = "gpt-5.2"
    AZURE_GPT52_API_VERSION: str = "2024-12-01-preview"
    AZURE_GPT5_DEPLOYMENT: str = "gpt-5"
    AZURE_GPT5_API_VERSION: str = "2025-01-01-preview"
    AZURE_GPT41_DEPLOYMENT: str = "gpt-4.1"
    AZURE_GPT41_API_VERSION: str = "2025-01-01-preview"

    # Default Model
    DEFAULT_MODEL: str = "gpt-5.2"

    # Azure Embedding
    AZURE_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-large"
    AZURE_EMBEDDING_API_VERSION: str = "2023-05-15"
    EMBEDDING_MODEL: str = "text-embedding-3-large"

    # Azure Document Intelligence
    AZURE_DOC_INTELLIGENCE_ENDPOINT: str = ""
    AZURE_DOC_INTELLIGENCE_KEY: str = ""

    # Azure Cohere Reranker
    AZURE_RERANKER_ENDPOINT: str = ""
    AZURE_RERANKER_API_KEY: str = ""
    AZURE_RERANKER_MODEL: str = "Cohere-rerank-v4.0-pro"

    # ChromaDB
    CHROMA_PERSIST_DIRECTORY: str = "../data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "maintenance_docs"

    # RAW PDFs Directory
    RAW_PDFS_DIRECTORY: str = "../data/raw_pdfs"

    # Document Intelligence Settings
    USE_AZURE_DOC_INTELLIGENCE: bool = True
    DOC_INTELLIGENCE_OUTPUT_FORMAT: str = "markdown"

    # Agentic RAG Settings
    USE_AGENTIC_RAG: bool = True
    MAX_AGENT_ITERATIONS: int = 5

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
