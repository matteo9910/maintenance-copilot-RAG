"""Azure OpenAI LLM Configuration."""
import httpx
from typing import Optional
from langchain_openai import AzureChatOpenAI
from app.core.config import settings


# Model ID -> display name and Azure deployment config
AVAILABLE_MODELS = {
    "gpt-5.2": "GPT-5.2 (Azure)",
    "gpt-5": "GPT-5 (Azure)",
    "gpt-4.1": "GPT-4.1 (Azure)",
}

# Model ID -> (deployment_name, api_version)
_MODEL_DEPLOYMENT_MAP = {
    "gpt-5.2": (settings.AZURE_GPT52_DEPLOYMENT, settings.AZURE_GPT52_API_VERSION),
    "gpt-5": (settings.AZURE_GPT5_DEPLOYMENT, settings.AZURE_GPT5_API_VERSION),
    "gpt-4.1": (settings.AZURE_GPT41_DEPLOYMENT, settings.AZURE_GPT41_API_VERSION),
}


def get_llm(model_id: Optional[str] = None, temperature: float = 0.3) -> AzureChatOpenAI:
    """
    Get LLM instance configured for Azure OpenAI.

    Args:
        model_id: Model ID (e.g., 'gpt-5.2'). Uses default if not provided.
        temperature: Sampling temperature (0-1).

    Returns:
        AzureChatOpenAI instance.
    """
    model = model_id or settings.DEFAULT_MODEL

    deployment, api_version = _MODEL_DEPLOYMENT_MAP.get(
        model,
        (settings.AZURE_GPT52_DEPLOYMENT, settings.AZURE_GPT52_API_VERSION)
    )

    # GPT-5 only supports temperature=1
    if model == "gpt-5":
        temperature = 1.0

    http_client = httpx.Client(verify=False)
    async_http_client = httpx.AsyncClient(verify=False)

    return AzureChatOpenAI(
        azure_deployment=deployment,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=api_version,
        temperature=temperature,
        http_client=http_client,
        http_async_client=async_http_client,
    )


def get_available_models() -> dict:
    """Get list of available models."""
    return AVAILABLE_MODELS
