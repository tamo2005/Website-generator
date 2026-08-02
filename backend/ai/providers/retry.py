"""
ai/providers/retry.py — RetryPolicy + FallbackChain

RetryPolicy: exponential backoff with configurable max attempts.
FallbackChain: try primary provider, fall back to alternates on exhaustion.

ADR-002: Only this module handles provider-level retries and fallback logic.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional

import httpx

from ai.providers.base import BaseProvider, GenerationConfig

logger = logging.getLogger("ai-site-gen")


@dataclass
class RetryPolicy:
    """
    Controls retry behavior for a single provider before fallback triggers.

    Retryable errors: network timeouts, rate limit (429), server error (5xx).
    Non-retryable: auth failure (401/403), bad request (400/422).
    """
    max_attempts: int = 3
    base_delay_s: float = 1.0
    exponential_backoff: bool = True
    retryable_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)

    def delay_for(self, attempt: int) -> float:
        """Return the delay in seconds before the given attempt number (1-indexed)."""
        if not self.exponential_backoff or attempt <= 1:
            return self.base_delay_s
        return self.base_delay_s * (2 ** (attempt - 1))


class FallbackChain:
    """
    Ordered list of providers to try when the primary provider fails.

    Behavior:
      1. Try primary provider up to RetryPolicy.max_attempts times.
      2. On final failure, try each fallback provider once.
      3. If all providers fail, raise the last exception.

    Example configuration (set in AIContainer):
        primary:   openrouter
        fallbacks: [gemini, ollama]
    """

    def __init__(
        self,
        primary: BaseProvider,
        fallbacks: list[BaseProvider],
        retry_policy: RetryPolicy,
    ) -> None:
        self.primary = primary
        self.fallbacks = fallbacks
        self.retry_policy = retry_policy
        self._last_used_provider: Optional[BaseProvider] = None
        self._fallback_triggered: bool = False

    @property
    def last_used_provider(self) -> Optional[BaseProvider]:
        return self._last_used_provider

    @property
    def fallback_triggered(self) -> bool:
        return self._fallback_triggered

    async def generate(
        self,
        messages: list[dict],
        config: GenerationConfig,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens, automatically retrying and falling back as needed."""
        self._fallback_triggered = False

        # Try primary with retries
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                self._last_used_provider = self.primary
                async for token in self.primary.generate(messages, config):
                    yield token
                return  # Success
            except Exception as exc:
                last_exc = exc
                is_retryable = self._is_retryable(exc)
                logger.warning(
                    f"Provider '{self.primary.name}' attempt {attempt}/{self.retry_policy.max_attempts} "
                    f"failed: {exc!r} | retryable={is_retryable}"
                )
                if not is_retryable or attempt == self.retry_policy.max_attempts:
                    break
                delay = self.retry_policy.delay_for(attempt)
                logger.info(f"Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)

        # Primary exhausted — try fallbacks
        self._fallback_triggered = True
        for fallback in self.fallbacks:
            try:
                logger.info(f"Falling back to provider: '{fallback.name}'")
                self._last_used_provider = fallback
                async for token in fallback.generate(messages, config):
                    yield token
                return  # Fallback succeeded
            except Exception as exc:
                last_exc = exc
                logger.warning(f"Fallback provider '{fallback.name}' failed: {exc!r}")
                continue

        # All providers failed
        raise RuntimeError(
            f"All providers failed. Primary: {self.primary.name}, "
            f"Fallbacks: {[p.name for p in self.fallbacks]}. "
            f"Last error: {last_exc!r}"
        )

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        """Determine if an exception warrants a retry."""
        if isinstance(exc, httpx.TimeoutException):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code in (429, 500, 502, 503, 504)
        if isinstance(exc, (ConnectionError, OSError)):
            return True
        return False
