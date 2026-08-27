from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: str = Field(..., description="system, user, or assistant")
    content: str = Field(..., description="Message text content")


class LLMResponse(BaseModel):
    content: str = Field(..., description="Generated text content")
    model: str = Field(..., description="Model identifier used")
    tokens_used: int = Field(default=0, description="Total tokens used if available")
    finish_reason: str = Field(default="stop", description="Finish reason")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional provider metadata")


class BaseLLMClient(ABC):
    """Abstract Base Class for LLM providers."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the required API keys or configurations are present."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the provider name (e.g. openai, ollama, mock)."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Returns the model name (e.g. gpt-4o-mini)."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generates a text completion given a list of chat messages."""
        pass

    def generate_sync(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Synchronous generation wrapper."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If running in an active loop, use a new thread or run_until_complete
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run,
                        self.generate(messages, temperature, max_tokens, **kwargs),
                    ).result()
            return loop.run_until_complete(
                self.generate(messages, temperature, max_tokens, **kwargs)
            )
        except RuntimeError:
            return asyncio.run(
                self.generate(messages, temperature, max_tokens, **kwargs)
            )
