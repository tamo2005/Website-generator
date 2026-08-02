"""
ai/pipeline/context.py — GenerationContext + WorkflowState (ADR-004)

GenerationContext is the single object that flows through the entire pipeline.
No loose argument lists anywhere in the pipeline code.

ADR-004: Adding a new field requires one line change here only.
         Zero downstream function signature changes.

WorkflowState: tracks the current status of a generation run.
               Future: enables queueing, pausing, and resuming generations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

if TYPE_CHECKING:
    from ai.metrics.tracker import AIMetrics, MetricsCollector
    from ai.pipeline.events import PipelineEvent
    from ai.providers.base import BaseProvider, GenerationConfig
    from ai.providers.retry import FallbackChain


class WorkflowState(str, Enum):
    """
    State machine for a generation run.
    Transitions are linear — future: allow pause/resume between states.

    queued → analyzing → planning → building → generating →
    validating → repairing → completed | failed
    """
    QUEUED      = "queued"
    ANALYZING   = "analyzing"    # PromptAnalyzer running
    PLANNING    = "planning"     # AIPlanner building GenerationPlan
    BUILDING    = "building"     # SpecBuilder building WebsiteSpec
    GENERATING  = "generating"   # ComponentRegistry generating HTML
    VALIDATING  = "validating"   # ValidatorChain running
    REPAIRING   = "repairing"    # RepairEngine running
    COMPLETED   = "completed"    # Version saved, pipeline done
    FAILED      = "failed"       # Unrecoverable error


@dataclass
class GenerationContext:
    """
    Single context object passed through the entire generation pipeline.

    FROZEN interface (ADR-004): do not add function arguments that duplicate
    what is already in this dataclass. Access everything via ctx.field.
    """
    # ── Identity ────────────────────────────────────────────────────────────
    request_id: str = field(default_factory=lambda: str(uuid4()))
    pipeline_version: str = "V1"         # ADR-008: stored with every version

    # ── Request source ───────────────────────────────────────────────────────
    # User and Project are ORM model instances. Import deferred to avoid circulars.
    user: Optional[object] = None        # models.User
    project: Optional[object] = None     # models.Project

    # ── Raw input ────────────────────────────────────────────────────────────
    raw_prompt: str = ""

    # ── Filled by Analyzer (WorkflowState.ANALYZING) ────────────────────────
    analysis: Optional[object] = None    # ai.planner.analyzer.PromptAnalysisResult

    # ── Filled by Planner (WorkflowState.PLANNING) ──────────────────────────
    plan: Optional[object] = None        # ai.planner.planner.GenerationPlan

    # ── Filled by SpecBuilder (WorkflowState.BUILDING) ──────────────────────
    spec: Optional[object] = None        # schemas.generation.WebsiteSpec

    # ── Filled by ThemeEngine ───────────────────────────────────────────────
    theme: Optional[object] = None       # ai.builders.theme_engine.ResolvedTheme

    # ── Provider configuration ───────────────────────────────────────────────
    provider: Optional["BaseProvider"] = None
    fallback_chain: Optional["FallbackChain"] = None
    generation_config: Optional["GenerationConfig"] = None

    # ── State machine ────────────────────────────────────────────────────────
    status: WorkflowState = WorkflowState.QUEUED
    events: list["PipelineEvent"] = field(default_factory=list)

    # ── Prompt versioning (ADR-009) ──────────────────────────────────────────
    # Maps prompt role → template version used. e.g. {"system": "1.0.0", "Hero": "1.0.0"}
    prompt_template_versions: dict[str, str] = field(default_factory=dict)

    # ── Generation results ───────────────────────────────────────────────────
    # Generated HTML for each component (ordered)
    component_html: list[str] = field(default_factory=list)
    # Fully assembled HTML before validation
    assembled_html: Optional[str] = None
    # HTML after repair passes (final output)
    final_html: Optional[str] = None
    # Number of repair loops completed
    repair_attempts: int = 0
    # Saved ProjectVersion ORM instance
    version: Optional[object] = None

    # ── Metrics ──────────────────────────────────────────────────────────────
    metrics: Optional["AIMetrics"] = None
    metrics_collector: Optional["MetricsCollector"] = None

    # ── Partial regeneration (Module J) ─────────────────────────────────────
    # Set to regenerate only one component, not the full page
    regenerate_component_type: Optional[str] = None

    def transition(self, new_state: WorkflowState) -> None:
        """Advance the workflow state."""
        self.status = new_state

    def is_partial_regen(self) -> bool:
        """True if this is a targeted single-component regeneration."""
        return self.regenerate_component_type is not None

    def summary(self) -> dict:
        """Lightweight summary for logging — no ORM objects."""
        return {
            "request_id": self.request_id,
            "pipeline_version": self.pipeline_version,
            "status": self.status.value,
            "prompt_length": len(self.raw_prompt),
            "repair_attempts": self.repair_attempts,
            "component_count": len(self.component_html),
        }
