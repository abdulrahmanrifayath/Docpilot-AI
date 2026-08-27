from typing import List, Optional, Dict, Any
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.llm.base import BaseLLMClient, LLMMessage, LLMResponse


class OpenAIClient(BaseLLMClient):
    """OpenAI-compatible HTTP Client (supports OpenAI, OpenRouter, Azure, Ollama /v1, Groq, etc.)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        self.api_key = api_key or settings.LLM_API_KEY or settings.OPENAI_API_KEY
        self.base_url = (base_url or settings.LLM_BASE_URL or settings.OPENAI_BASE_URL).rstrip("/")
        self.model = model or settings.LLM_MODEL or settings.OPENAI_MODEL
        self.temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        self.max_tokens = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS

    def is_configured(self) -> bool:
        # If calling a local provider like Ollama/LMStudio, API key might be optional or dummy
        if "localhost" in self.base_url or "127.0.0.1" in self.base_url:
            return True
        return bool(self.api_key and len(self.api_key.strip()) > 3)

    def get_provider_name(self) -> str:
        return "openai"

    def get_model_name(self) -> str:
        return self.model

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        if not self.is_configured():
            raise ValueError(
                "LLM API Key is not configured. Please set LLM_API_KEY or OPENAI_API_KEY in environment or settings."
            )

        endpoint = f"{self.base_url}/chat/completions"
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            **kwargs,
        }

        logger.info(f"Calling LLM ({self.model}) at {endpoint}")

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                choice = data.get("choices", [{}])[0]
                message_content = choice.get("message", {}).get("content", "")
                finish_reason = choice.get("finish_reason", "stop")
                usage = data.get("usage", {})
                tokens_used = usage.get("total_tokens", 0)

                return LLMResponse(
                    content=message_content,
                    model=data.get("model", self.model),
                    tokens_used=tokens_used,
                    finish_reason=finish_reason,
                    metadata={"usage": usage},
                )
            except httpx.HTTPStatusError as e:
                logger.error(f"LLM API HTTP Error: {e.response.status_code} - {e.response.text}")
                raise RuntimeError(f"LLM API request failed with status {e.response.status_code}: {e.response.text}")
            except Exception as e:
                logger.error(f"LLM Connection Error: {str(e)}")
                raise RuntimeError(f"Failed to communicate with LLM provider: {str(e)}")
