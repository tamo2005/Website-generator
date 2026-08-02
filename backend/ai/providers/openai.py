"""
ai/providers/openai.py — OpenAIProvider (STUB)

Wired when OPENAI_API_KEY is configured in Phase 3.
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
    max_context_tokens=128_000,
    models=("gpt-4o", "gpt-4o-mini", "gpt-4-turbo"),
)


class OpenAIProvider(BaseProvider):
    """
    OpenAI GPT provider — Phase 3 implementation.

    To activate:
      1. Add OPENAI_API_KEY to .env
      2. Install: pip install openai
      3. Replace NotImplementedError bodies with openai SDK calls
    """
    name = "openai"
    capabilities = _CAPABILITIES

    async def generate(
        self,
        messages: list[dict],
        config: GenerationConfig,
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError(
            "OpenAIProvider is stubbed for Phase 3. "
            "Use OpenRouterProvider or GeminiProvider instead."
        )
        yield  # Make this a valid async generator

    async def generate_structured(
        self,
        messages: list[dict],
        schema: Type[BaseModel],
        config: GenerationConfig,
    ) -> BaseModel:
        raise NotImplementedError("OpenAIProvider is stubbed for Phase 3.")

    async def health_check(self) -> bool:
        return False  # Not available — always falls back
