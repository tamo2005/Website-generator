"""
ai/providers/base.py — Frozen provider interface (ADR-002, ADR-010)

BaseProvider is the ONLY interface through which any LLM is called.
Zero code outside ai/providers/ may call LLM APIs directly.

ProviderCapabilities defines what a provider can do.
Route decisions ALWAYS use capabilities, never provider name strings (ADR-010).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, AsyncGenerator, Optional, Type

from pydantic import BaseModel

if TYPE_CHECKING:
    pass


# ── Capability Interface ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProviderCapabilities:
    """
    Describes what this provider can do.
    Used for capability-based routing — never use provider name checks.

    Example:
        # ✅ Correct
        if provider.capabilities.supports_json:
            result = await provider.generate_structured(...)

        # ❌ Wrong — brittle, breaks when new providers are added
        if provider.name == "openai":
            ...
    """
    supports_streaming: bool
    supports_tools: bool         # Function calling / tool use
    supports_json: bool          # Native JSON mode / structured output
    supports_images: bool        # Can receive image inputs
    supports_vision: bool        # Can understand/describe images
    max_context_tokens: int
    models: tuple[str, ...]      # Available model IDs for this provider


# ── Generation Config ────────────────────────────────────────────────────────

class GenerationConfig(BaseModel):
    """Parameters passed to the provider for a single generation call."""
    model: str
    temperature: float = 0.6
    top_p: float = 0.95
    max_tokens: int = 4096
    stream: bool = True
    json_mode: bool = False      # Activates structured output if supported


# ── Base Provider ────────────────────────────────────────────────────────────

class BaseProvider(ABC):
    """
    Abstract base class for all LLM providers.

    Subclasses must implement:
      - generate(): stream raw text tokens
      - generate_structured(): return a validated Pydantic model
      - health_check(): verify the provider is reachable

    All public attributes are read-only after construction.
    """

    # Subclasses must define these class-level attributes
    name: str
    capabilities: ProviderCapabilities

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        config: GenerationConfig,
    ) -> AsyncGenerator[str, None]:
        """
        Stream text tokens from the provider.

        Args:
            messages: OpenAI-format message list
                      [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
            config:   GenerationConfig with model, temperature, max_tokens, etc.

        Yields:
            str: individual text tokens as they arrive
        """
        ...

    @abstractmethod
    async def generate_structured(
        self,
        messages: list[dict],
        schema: Type[BaseModel],
        config: GenerationConfig,
    ) -> BaseModel:
        """
        Return a fully validated Pydantic model from the provider.

        Requires: provider.capabilities.supports_json == True

        Args:
            messages: OpenAI-format message list
            schema:   Pydantic model class to validate and return
            config:   GenerationConfig — json_mode will be set to True

        Returns:
            An instance of `schema` populated from the provider's JSON response
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Return True if the provider is reachable and responding.
        Used by the FallbackChain to select an available provider.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
