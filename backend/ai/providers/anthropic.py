"""
ai/providers/anthropic.py — AnthropicProvider (STUB)

Wired when ANTHROPIC_API_KEY is configured in Phase 3.
The interface is fully defined — only the implementation is pending.
"""
from __future__ import annotations

from typing import AsyncGenerator, Type

from pydantic import BaseModel

from ai.providers.base import BaseProvider, GenerationConfig, ProviderCapabilities

_CAPABILITIES = ProviderCapabilities(
    supports_streaming=True,
    supports_tools=True,
    supports_json=True,
    supports_images=True,
    supports_vision=True,
    max_context_tokens=200_000,
    models=("claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"),
)


class AnthropicProvider(BaseProvider):
    """
    Anthropic Claude provider — Phase 3 implementation.

    To activate:
      1. Add ANTHROPIC_API_KEY to .env
      2. Install: pip install anthropic
      3. Replace NotImplementedError bodies with anthropic SDK calls
    """
    name = "anthropic"
    capabilities = _CAPABILITIES

    async def generate(
        self,
        messages: list[dict],
        config: GenerationConfig,
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError(
            "AnthropicProvider is stubbed for Phase 3. "
            "Use OpenRouterProvider or GeminiProvider instead."
        )
        yield

    async def generate_structured(
        self,
        messages: list[dict],
        schema: Type[BaseModel],
        config: GenerationConfig,
    ) -> BaseModel:
        raise NotImplementedError("AnthropicProvider is stubbed for Phase 3.")

    async def health_check(self) -> bool:
        return False
