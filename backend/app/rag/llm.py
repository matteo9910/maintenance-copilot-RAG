"""OpenRouter LLM Configuration."""
import httpx
from typing import Optional
from langchain_openai import ChatOpenAI
from app.core.config import settings


# Available models via OpenRouter
AVAILABLE_MODELS = {
    "anthropic/claude-sonnet-4.5": "Claude Sonnet 4.5 (Anthropic)",
    "openai/chatgpt-4o-latest": "ChatGPT-4o Latest (OpenAI)",
    "google/gemini-3-pro-preview": "Gemini 3 Pro Preview (Google)"
}


def get_llm(model_id: Optional[str] = None, temperature: float = 0.3) -> ChatOpenAI:
    """
    Get LLM instance configured for OpenRouter.

    Args:
        model_id: Model ID (e.g., 'openai/gpt-4o'). Uses default if not provided.
        temperature: Sampling temperature (0-1).

    Returns:
        ChatOpenAI instance configured for OpenRouter.
    """
    model = model_id or settings.DEFAULT_MODEL

    # Create custom http clients that handle corporate SSL certificates
    http_client = httpx.Client(verify=False)
    async_http_client = httpx.AsyncClient(verify=False)

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=settings.OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Maintenance AI Copilot"
        },
        http_client=http_client,
        http_async_client=async_http_client
    )


def get_available_models() -> dict:
    """Get list of available models."""
    return AVAILABLE_MODELS
