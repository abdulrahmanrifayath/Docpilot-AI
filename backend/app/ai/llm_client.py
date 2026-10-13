import abc
import json
import logging
from typing import AsyncGenerator, Optional, Dict, Any, List
import httpx

from app.core.config import settings

logger = logging.getLogger("docpilot")


class LLMNotConfiguredError(Exception):
    """Raised when an LLM operation is requested but the provider is not configured."""
    def __init__(self, message: str = "LLM provider is not configured with an API key", provider: str = "unknown"):
        super().__init__(message)
        self.message = message
        self.provider = provider


class LLMClient(abc.ABC):
    """Abstract Base Class for LLM providers."""

    @abc.abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        """Generate text completion from prompt and optional system prompt."""
        pass

    @abc.abstractmethod
    async def generate_stream(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Stream token chunks from prompt."""
        pass

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Check if LLM provider has necessary credentials and configuration."""
        pass

    @abc.abstractmethod
    def get_model_name(self) -> str:
        """Return currently configured model name."""
        pass

    @abc.abstractmethod
    def get_provider_name(self) -> str:
        """Return provider type name."""
        pass


class OpenAICompatibleClient(LLMClient):
    """
    OpenAI-compatible LLM Client.
    Works with OpenAI, OpenRouter, Ollama, vLLM, LocalAI, Azure OpenAI, and custom endpoints.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_name: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        self._provider = (provider_name or settings.LLM_PROVIDER or "openai").lower()
        self._api_key = api_key if api_key is not None else settings.LLM_API_KEY
        self._model = model or settings.LLM_MODEL or "gpt-4o-mini"
        self._base_url = (base_url or settings.LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self._timeout = timeout

    def is_configured(self) -> bool:
        # Local / self-hosted endpoints (e.g. Ollama, local) do not require cloud API keys
        if self._provider in ("ollama", "local", "mock"):
            return True
        return bool(self._api_key and len(self._api_key.strip()) > 0)

    def get_model_name(self) -> str:
        return self._model

    def get_provider_name(self) -> str:
        return self._provider

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key and len(self._api_key.strip()) > 0:
            headers["Authorization"] = f"Bearer {self._api_key.strip()}"
        return headers

    def _build_messages(self, prompt: str, system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        if not self.is_configured():
            raise LLMNotConfiguredError(
                f"LLM Provider '{self._provider}' is not configured. Please supply an API key in Settings.",
                provider=self._provider,
            )

        messages = self._build_messages(prompt, system_prompt)
        headers = self._build_headers()
        temperature = kwargs.get("temperature", 0.2)
        max_tokens = kwargs.get("max_tokens", 4000)

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        endpoint = f"{self._base_url}/chat/completions"
        logger.info(f"Dispatching LLM generation to {self._provider} model '{self._model}' at {endpoint}")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices")
            if not choices or not isinstance(choices, list):
                raise ValueError(f"Invalid response from LLM endpoint: {data}")
            return choices[0]["message"]["content"]

    async def generate_stream(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        if not self.is_configured():
            raise LLMNotConfiguredError(
                f"LLM Provider '{self._provider}' is not configured.",
                provider=self._provider,
            )

        messages = self._build_messages(prompt, system_prompt)
        headers = self._build_headers()
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
            "stream": True,
        }

        endpoint = f"{self._base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        raw = line[6:]
                        try:
                            chunk = json.loads(raw)
                            delta = chunk["choices"][0].get("delta", {}).get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            continue


class MockLLMClient(LLMClient):
    """Mock LLM client for automated testing and deterministic responses without external network access."""

    def __init__(self, model_name: str = "mock-docpilot-v1") -> None:
        self._model = model_name
        self._configured = True
        self.custom_responses: Dict[str, str] = {}

    def is_configured(self) -> bool:
        return self._configured

    def set_configured(self, val: bool) -> None:
        self._configured = val

    def get_model_name(self) -> str:
        return self._model

    def get_provider_name(self) -> str:
        return "mock"

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        if not self.is_configured():
            raise LLMNotConfiguredError("Mock LLM client set to unconfigured state", provider="mock")

        # Return custom registered response if matched
        for key, resp in self.custom_responses.items():
            if key in prompt or (system_prompt and key in system_prompt):
                return resp

        # Generate structured deterministic technical documentation
        doc_type = "TECHNICAL SPECIFICATION"
        if "README" in prompt:
            doc_type = "PROJECT README"
        elif "API" in prompt:
            doc_type = "API DOCUMENTATION"
        elif "DATABASE" in prompt:
            doc_type = "DATABASE SCHEMA DOCUMENTATION"
        elif "ARCHITECTURE" in prompt:
            doc_type = "SYSTEM ARCHITECTURE SPECIFICATION"

        return (
            f"# {doc_type}\n\n"
            "## Summary\n"
            "This document was synthesized from verified repository analysis data.\n\n"
            "### Detected Components\n"
            "- Facts derived from AST code parsing and schema discovery.\n"
            "- Strictly grounded in supplied repository metadata.\n\n"
            "```typescript\n"
            "// Source verified\n"
            "export const verified = true;\n"
            "```\n"
        )

    async def generate_stream(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        if not self.is_configured():
            raise LLMNotConfiguredError("Mock LLM client set to unconfigured state", provider="mock")
        content = await self.generate(prompt, system_prompt, **kwargs)
        for word in content.split(" "):
            yield word + " "


def create_llm_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMClient:
    """Factory creating an LLM client according to configured provider."""
    prov = (provider or settings.LLM_PROVIDER or "openai").lower()
    if prov == "mock":
        return MockLLMClient(model_name=model or "mock-docpilot-v1")
    # All common providers (OpenAI, OpenRouter, Groq, DeepSeek, Ollama, vLLM, etc.)
    # conform to the standard OpenAI-compatible API
    return OpenAICompatibleClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        provider_name=prov,
    )


# Default client instance
default_llm_client = create_llm_client()
get_llm_client = create_llm_client
