"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenRouter API
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # OpenAI API (for Embeddings)
    OPENAI_API_KEY: str = ""

    # LlamaCloud API (for LlamaParse)
    LLAMA_CLOUD_API_KEY: str = ""

    # Default Model
    DEFAULT_MODEL: str = "openai/gpt-4o"

    # ChromaDB
    CHROMA_PERSIST_DIRECTORY: str = "../data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "maintenance_docs"

    # Embedding Model (OpenAI)
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # RAW PDFs Directory
    RAW_PDFS_DIRECTORY: str = "../data/raw_pdfs"

    # LlamaParse Settings
    USE_LLAMA_PARSE: bool = True  # Set to False to use legacy PyPDFLoader
    LLAMA_PARSE_RESULT_TYPE: str = "markdown"  # "markdown" or "text"

    # Agentic RAG Settings
    USE_AGENTIC_RAG: bool = True  # Set to False to use legacy linear chain
    MAX_AGENT_ITERATIONS: int = 5  # Maximum number of retrieval hops

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
