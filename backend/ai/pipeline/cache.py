"""
ai/pipeline/cache.py — GenerationCache + CachePolicy (ADR-011)

SHA256(prompt + model + template_version) → Redis key → cached HTML.

CachePolicy explicitly defines what is and isn't cacheable.
No implicit "cache everything" behavior.

ADR-011: Cache policy is a first-class type, not scattered conditionals.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional

from core.config import get_settings

logger = logging.getLogger("ai-site-gen")

settings = get_settings()


class CachePolicy:
    """
    Defines exactly what generations are eligible for caching.

    Cached:     identical prompt + model + template_version, prompt >= min_length
    Not cached: repair runs, partial regenerations, prompts below min_length,
                when cache is disabled globally (ENABLE_AI_CACHE=false)
    """

    def __init__(
        self,
        enabled: bool = True,
        ttl_seconds: int = 3600,
        min_prompt_length: int = 10,
        exclude_repair_runs: bool = True,
        exclude_partial_regen: bool = True,
    ) -> None:
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.min_prompt_length = min_prompt_length
        self.exclude_repair_runs = exclude_repair_runs
        self.exclude_partial_regen = exclude_partial_regen

    def is_cacheable(
        self,
        prompt: str,
        is_repair: bool = False,
        is_partial: bool = False,
    ) -> bool:
        """Return True if this generation result should be cached."""
        if not self.enabled:
            return False
        if len(prompt) < self.min_prompt_length:
            return False
        if is_repair and self.exclude_repair_runs:
            return False
        if is_partial and self.exclude_partial_regen:
            return False
        return True

    @classmethod
    def from_settings(cls) -> "CachePolicy":
        return cls(
            enabled=settings.ENABLE_AI_CACHE,
            ttl_seconds=settings.AI_CACHE_TTL_SECONDS,
            min_prompt_length=settings.AI_CACHE_MIN_PROMPT_LENGTH,
        )


class GenerationCache:
    """
    Redis-backed cache for generation results.

    Key format: sha256(prompt + "::" + model + "::" + template_version)
    Value: JSON-encoded {"html": str, "metadata": dict}
    """

    def __init__(self, redis_client, policy: CachePolicy) -> None:
        self._redis = redis_client
        self.policy = policy

    def make_key(
        self,
        prompt: str,
        model: str,
        template_version: str,
    ) -> str:
        """
        Produce a deterministic cache key.
        SHA256 of concatenated inputs — collision-safe, consistent across restarts.
        """
        raw = f"{prompt}::{model}::{template_version}"
        return "gen_cache:" + hashlib.sha256(raw.encode()).hexdigest()

    async def get(self, key: str) -> Optional[str]:
        """Return cached HTML string, or None on miss."""
        if self._redis is None:
            return None
        try:
            cached = await self._redis.get(key)
            if cached:
                data = json.loads(cached)
                return data.get("html")
        except Exception as exc:
            logger.warning(f"Cache get failed for key {key[:20]}...: {exc}")
        return None

    async def set(
        self,
        key: str,
        html: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Store HTML in cache with TTL from policy."""
        if self._redis is None:
            return
        try:
            payload = json.dumps({"html": html, "metadata": metadata or {}})
            await self._redis.setex(key, self.policy.ttl_seconds, payload)
            logger.debug(f"Cached generation: {key[:20]}... TTL={self.policy.ttl_seconds}s")
        except Exception as exc:
            logger.warning(f"Cache set failed: {exc}")

    async def invalidate(self, key: str) -> None:
        """Remove a specific cache entry."""
        if self._redis is None:
            return
        try:
            await self._redis.delete(key)
        except Exception as exc:
            logger.warning(f"Cache invalidate failed: {exc}")
