"""
ai/pipeline/events.py — PipelineEvent + EventBus (ADR-007)

Every stage of the generation pipeline emits a typed PipelineEvent.
Events are:
  - Appended to GenerationContext.events for the full session record
  - Logged via structlog for real-time debugging
  - Future: streamed as SSE to the frontend for live progress UI

ADR-007: PipelineEvents are the single observability primitive.
         No scattered logger.info() calls across pipeline modules.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

import structlog

if TYPE_CHECKING:
    from ai.pipeline.context import GenerationContext

logger = structlog.get_logger("ai.pipeline")


class PipelineEventType(str, Enum):
    # Lifecycle
    GENERATION_STARTED     = "generation.started"
    GENERATION_COMPLETE    = "generation.complete"
    GENERATION_FAILED      = "generation.failed"

    # Intelligence layer
    CACHE_HIT              = "cache.hit"
    CACHE_MISS             = "cache.miss"
    CACHE_STORED           = "cache.stored"
    PROMPT_ANALYZED        = "prompt.analyzed"
    PLAN_BUILT             = "plan.built"
    SPEC_BUILT             = "spec.built"
    THEME_RESOLVED         = "theme.resolved"

    # Component generation
    COMPONENT_STARTED      = "component.started"
    COMPONENT_COMPLETE     = "component.complete"
    COMPONENT_FAILED       = "component.failed"
    HTML_ASSEMBLED         = "html.assembled"

    # Validation
    VALIDATION_STARTED     = "validation.started"
    VALIDATION_PASSED      = "validation.passed"
    VALIDATION_FAILED      = "validation.failed"

    # Repair
    REPAIR_STARTED         = "repair.started"
    REPAIR_COMPLETE        = "repair.complete"
    REPAIR_EXHAUSTED       = "repair.exhausted"

    # Storage
    VERSION_SAVED          = "version.saved"

    # Provider
    PROVIDER_FALLBACK      = "provider.fallback"
    PROVIDER_RETRY         = "provider.retry"


@dataclass
class PipelineEvent:
    """A single pipeline event with timestamp, type, and contextual data."""
    type: PipelineEventType
    timestamp: datetime
    data: dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None


class EventBus:
    """
    Emits PipelineEvents to:
      1. GenerationContext.events (in-memory record for the session)
      2. structlog (real-time log output)

    Usage:
        bus = EventBus(enabled=settings.ENABLE_PIPELINE_EVENTS)
        bus.emit(ctx, PipelineEventType.PROMPT_ANALYZED, website_type="landing")
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._stage_start_times: dict[str, float] = {}

    def emit(
        self,
        ctx: "GenerationContext",
        event_type: PipelineEventType,
        **data: Any,
    ) -> PipelineEvent:
        """Emit an event and attach it to the context."""
        now = datetime.now(timezone.utc)
        duration_ms = self._pop_duration(event_type.value)

        event = PipelineEvent(
            type=event_type,
            timestamp=now,
            data=data,
            duration_ms=duration_ms,
        )

        ctx.events.append(event)

        if self.enabled:
            log_data = {
                "request_id": ctx.request_id,
                "pipeline": ctx.pipeline_version,
                "event": event_type.value,
                **data,
            }
            if duration_ms is not None:
                log_data["duration_ms"] = round(duration_ms, 1)
            logger.info("pipeline_event", **log_data)

        return event

    def stage_start(self, stage_key: str) -> None:
        """Mark the start of a timed stage. Call before starting work."""
        self._stage_start_times[stage_key] = time.perf_counter()

    def _pop_duration(self, event_key: str) -> Optional[float]:
        """Compute duration from the matching stage_start() call, if any."""
        # Match events to stages by prefix
        for key in list(self._stage_start_times.keys()):
            if event_key.startswith(key.split(".")[0]):
                start = self._stage_start_times.pop(key)
                return (time.perf_counter() - start) * 1000
        return None
