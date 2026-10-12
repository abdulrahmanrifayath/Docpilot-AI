from fastapi import APIRouter
from app.core.config import settings
from app.schemas.repository import ProviderSettings, ProviderSettingsUpdate
from app.ai.llm_provider import llm_provider

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=ProviderSettings)
async def get_settings():
    """Retrieve active AI provider and integration settings."""
    return ProviderSettings(
        llm_provider=settings.LLM_PROVIDER,
        llm_model=settings.LLM_MODEL,
        llm_base_url=settings.LLM_BASE_URL,
        is_configured=llm_provider.is_configured(),
        available_providers=["openai", "gemini", "anthropic", "ollama", "custom"],
        github_token_configured=bool(settings.GITHUB_TOKEN and len(settings.GITHUB_TOKEN.strip()) > 0),
    )


@router.post("", response_model=ProviderSettings)
async def update_settings(payload: ProviderSettingsUpdate):
    """Update runtime AI provider keys and models."""
    if payload.llm_provider is not None:
        settings.LLM_PROVIDER = payload.llm_provider
        llm_provider.provider = payload.llm_provider

    if payload.llm_api_key is not None:
        settings.LLM_API_KEY = payload.llm_api_key
        llm_provider.api_key = payload.llm_api_key

    if payload.llm_model is not None:
        settings.LLM_MODEL = payload.llm_model
        llm_provider.model = payload.llm_model

    if payload.llm_base_url is not None:
        settings.LLM_BASE_URL = payload.llm_base_url
        llm_provider.base_url = payload.llm_base_url

    if payload.github_token is not None:
        settings.GITHUB_TOKEN = payload.github_token

    return ProviderSettings(
        llm_provider=settings.LLM_PROVIDER,
        llm_model=settings.LLM_MODEL,
        llm_base_url=settings.LLM_BASE_URL,
        is_configured=llm_provider.is_configured(),
        available_providers=["openai", "gemini", "anthropic", "ollama", "custom"],
        github_token_configured=bool(settings.GITHUB_TOKEN and len(settings.GITHUB_TOKEN.strip()) > 0),
    )
