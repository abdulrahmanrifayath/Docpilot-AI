from typing import Optional
from backend.app.core.config import settings
from backend.app.llm.base import BaseLLMClient
from backend.app.llm.openai_client import OpenAIClient
from backend.app.llm.mock_client import MockLLMClient


def get_llm_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    force_mock: bool = False,
) -> BaseLLMClient:
    """Factory to instantiate the appropriate LLM client based on configuration."""
    if force_mock:
        return MockLLMClient()

    selected_provider = (provider or settings.LLM_PROVIDER or "openai").lower()

    if selected_provider == "mock":
        return MockLLMClient(model_name=model or settings.LLM_MODEL or "mock-docpilot-v1")

    # OpenAI-compatible providers (supports OpenAI, OpenRouter, Azure, Ollama /v1, Groq, etc.)
    return OpenAIClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
