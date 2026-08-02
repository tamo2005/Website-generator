"""
ai/metrics/tracker.py — AIMetrics + MetricsCollector

AIMetrics is the standalone dataclass that lives in GenerationContext
AND is persisted to the database as GenerationMetrics (ORM model).

Fields tracked per generation:
  - Provider, model, prompt template version (ADR-009)
  - Token counts and estimated cost
  - Latency: total, TTFT, per-component
  - Repair count and success status
  - Cache hit / fallback used

Phase 2: MetricsCollector is a lightweight helper for updating AIMetrics
         during pipeline execution without passing metrics everywhere.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AIMetrics:
    """
    All metrics for a single generation run.
    Attached to GenerationContext.metrics and persisted to DB at completion.
    """
    # Identity
    request_id: str = ""
    pipeline_version: str = "V1"
    provider: str = ""
    model: str = ""
    prompt_template_version: str = ""   # ADR-009: which template produced this output

    # Token counts
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    # Timing (milliseconds)
    total_latency_ms: float = 0.0
    ttft_ms: float = 0.0                # Time to first token
    per_component_ms: dict[str, float] = field(default_factory=dict)

    # Quality
    component_count: int = 0
    repair_count: int = 0
    repair_succeeded: bool = False
    validation_score: float = 0.0
    cache_hit: bool = False

    # Provider reliability
    fallback_used: bool = False
    fallback_provider: Optional[str] = None
    provider_errors: list[str] = field(default_factory=list)

    # Cost
    estimated_cost_usd: float = 0.0

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict for storage in metadata_json."""
        return {
            "request_id": self.request_id,
            "pipeline_version": self.pipeline_version,
            "provider": self.provider,
            "model": self.model,
            "prompt_template_version": self.prompt_template_version,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "ttft_ms": round(self.ttft_ms, 1),
            "per_component_ms": {k: round(v, 1) for k, v in self.per_component_ms.items()},
            "component_count": self.component_count,
            "repair_count": self.repair_count,
            "repair_succeeded": self.repair_succeeded,
            "validation_score": round(self.validation_score, 3),
            "cache_hit": self.cache_hit,
            "fallback_used": self.fallback_used,
            "fallback_provider": self.fallback_provider,
            "provider_errors": self.provider_errors,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
        }


class MetricsCollector:
    """
    Helper for updating AIMetrics during pipeline execution.
    Wraps timing and accumulation so pipeline modules stay clean.
    """

    def __init__(self, metrics: AIMetrics) -> None:
        self._metrics = metrics
        self._start_time: Optional[float] = None
        self._component_timers: dict[str, float] = {}

    @property
    def metrics(self) -> AIMetrics:
        return self._metrics

    def start_generation(self) -> None:
        self._start_time = time.perf_counter()

    def record_ttft(self) -> None:
        """Call when the first token arrives from the provider."""
        if self._start_time:
            self._metrics.ttft_ms = (time.perf_counter() - self._start_time) * 1000

    def finish_generation(self) -> None:
        if self._start_time:
            self._metrics.total_latency_ms = (
                (time.perf_counter() - self._start_time) * 1000
            )

    def start_component(self, component_type: str) -> None:
        self._component_timers[component_type] = time.perf_counter()

    def finish_component(self, component_type: str) -> None:
        start = self._component_timers.pop(component_type, None)
        if start:
            self._metrics.per_component_ms[component_type] = (
                (time.perf_counter() - start) * 1000
            )
        self._metrics.component_count += 1

    def add_tokens(self, prompt: int = 0, completion: int = 0) -> None:
        self._metrics.prompt_tokens += prompt
        self._metrics.completion_tokens += completion

    def record_repair(self, succeeded: bool) -> None:
        self._metrics.repair_count += 1
        self._metrics.repair_succeeded = succeeded

    def record_fallback(self, fallback_provider: str) -> None:
        self._metrics.fallback_used = True
        self._metrics.fallback_provider = fallback_provider

    def record_error(self, error: str) -> None:
        self._metrics.provider_errors.append(error)
