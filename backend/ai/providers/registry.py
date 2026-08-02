"""
ai/providers/registry.py — ProviderRegistry

Injected into the DI container — never instantiated as a module-level singleton.
All providers are registered at startup via AIContainer.

ADR-002: Zero code outside ai/providers/ calls LLM APIs directly.
ADR-010: Use capability-based routing, never provider name strings.
"""
from __future__ import annotations

import logging
from typing import Optional

from ai.providers.base import BaseProvider

logger = logging.getLogger("ai-site-gen")


class UnknownProviderError(Exception):
    """Raised when requesting a provider that has not been registered."""
    pass


class ProviderRegistry:
    """
    Registry of all available providers.

    Populated by the DI container (ai/core/container.py) at startup.
    Use .get() to retrieve a provider by name.
    Use .default() to get the configured default provider.
    """

    def __init__(self, default_provider_name: str) -> None:
        self._providers: dict[str, BaseProvider] = {}
        self._default_name = default_provider_name

    def register(self, provider: BaseProvider) -> None:
        """Register a provider instance."""
        self._providers[provider.name] = provider
        logger.debug(f"Provider registered: {provider.name}")

    def get(self, name: str) -> BaseProvider:
        """
        Return a provider by name.
        Raises UnknownProviderError if the provider is not registered.
        """
        provider = self._providers.get(name)
        if provider is None:
            available = list(self._providers.keys())
            raise UnknownProviderError(
                f"Provider '{name}' is not registered. "
                f"Available providers: {available}"
            )
        return provider

    def default(self) -> BaseProvider:
        """Return the default provider (configured via DEFAULT_PROVIDER in .env)."""
        return self.get(self._default_name)

    def available(self) -> list[str]:
        """Return names of all registered providers."""
        return list(self._providers.keys())

    async def find_healthy(self, preferred: Optional[str] = None) -> Optional[BaseProvider]:
        """
        Return the first healthy provider, starting from `preferred`.
        Used by FallbackChain to select a live provider.
        """
        candidates = (
            [preferred] + [n for n in self.available() if n != preferred]
            if preferred
            else self.available()
        )
        for name in candidates:
            try:
                provider = self.get(name)
                if await provider.health_check():
                    return provider
            except (UnknownProviderError, Exception):
                continue
        return None
