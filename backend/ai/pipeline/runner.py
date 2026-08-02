"""
ai/pipeline/runner.py — GenerationPipelineV1: Full Orchestrator

Wires all 9 modules into a single pipeline:

  Prompt
    ↓  Module 1
  PromptAnalyzer
    ↓  Module 2
  AIPlanner
    ↓  Module 3
  SpecBuilder → WebsiteSpec
    ↓  Module 4
  ThemeEngine → ResolvedTheme
    ↓  Module 5+6
  ComponentRegistry → Component HTML fragments
    ↓  Module 7
  HTMLBuilder → Full HTML
    ↓  Module 8
  ValidatorChain → ValidationReport
    ↓  Module 9
  RepairEngine → Final HTML

The pipeline uses GenerationContext as the state container.
Events are emitted at each stage for observability.

Usage:
    pipeline = GenerationPipelineV1(provider, config)
    result = await pipeline.run("Build a SaaS landing page for an AI startup")
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, AsyncGenerator, Optional

from ai.builders.html_builder import HTMLBuilder
from ai.builders.theme_engine import ResolvedTheme, ThemeEngine
from ai.planner.analyzer import PromptAnalyzer
from ai.planner.planner import AIPlanner
from ai.planner.spec_builder import SpecBuilder
from ai.registry.generators.all_generators import create_default_registry
from ai.repair.engine import RepairEngine
from ai.validators.chain import ValidatorChain, ValidationReport
from evaluation.evaluator import WebsiteEvaluator
from evaluation.rubric import EvaluationResult
from schemas.generation import (
    GenerationPlan,
    PromptAnalysisResult,
    WebsiteSpec,
)

if TYPE_CHECKING:
    from ai.providers.base import BaseProvider, GenerationConfig
    from ai.registry.component_registry import ComponentRegistry

logger = logging.getLogger("ai-site-gen")


# ── Pipeline Result ──────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    """Complete result from a pipeline run."""
    html: str
    body_html: str                       # Body-only HTML for streaming preview
    spec: WebsiteSpec
    analysis: PromptAnalysisResult
    plan: GenerationPlan
    theme: ResolvedTheme
    validation: ValidationReport
    evaluation: Optional[EvaluationResult] = None  # Sprint 1: Quality scores
    elapsed_seconds: float = 0.0
    component_count: int = 0
    pipeline_version: str = "V1"
    success: bool = True
    error: Optional[str] = None


# ── Pipeline V1 ──────────────────────────────────────────────────────────────

class GenerationPipelineV1:
    """
    Full generation pipeline orchestrator.

    Wires Modules 1-9 into a single async flow.
    Stateless — all state flows through method args.
    """

    def __init__(
        self,
        provider: "BaseProvider",
        config: "GenerationConfig",
        registry: Optional["ComponentRegistry"] = None,
    ) -> None:
        self._provider = provider
        self._config = config
        self._registry = registry or create_default_registry()

        # Module instances (stateless)
        self._analyzer = PromptAnalyzer()
        self._planner = AIPlanner()
        self._spec_builder = SpecBuilder()
        self._theme_engine = ThemeEngine()
        self._html_builder = HTMLBuilder()
        self._validator_chain = ValidatorChain.default()
        self._repair_engine = RepairEngine()
        self._evaluator = WebsiteEvaluator()

    async def run(self, prompt: str) -> PipelineResult:
        """
        Execute the full generation pipeline.

        Prompt → Analysis → Plan → Spec → Theme → Components → HTML → Validate → Repair
        """
        start = time.perf_counter()

        try:
            # ── Module 1: Prompt Analysis ─────────────────────────────────
            logger.info("Pipeline: Module 1 — Analyzing prompt")
            analysis = self._analyzer.analyze(prompt)
            logger.info(
                f"  → type={analysis.website_type.value} "
                f"industry={analysis.industry} "
                f"theme={analysis.theme.value} "
                f"components={analysis.requested_components}"
            )

            # ── Module 2: Planning ────────────────────────────────────────
            logger.info("Pipeline: Module 2 — Planning components")
            plan = self._planner.plan(analysis)
            logger.info(
                f"  → {plan.total_components} components, "
                f"~{plan.estimated_tokens} tokens"
            )

            # ── Module 3: WebsiteSpec ─────────────────────────────────────
            logger.info("Pipeline: Module 3 — Building WebsiteSpec")
            spec = self._spec_builder.build(analysis, plan)
            logger.info(f"  → site={spec.site_name} pages={len(spec.pages)}")

            # ── Module 4: Theme Resolution ────────────────────────────────
            logger.info("Pipeline: Module 4 — Resolving theme")
            theme = self._theme_engine.resolve(spec.theme, analysis)
            logger.info(
                f"  → mode={theme.mode.value} "
                f"primary={theme.colors.primary} "
                f"font={theme.heading_font}"
            )

            # ── Module 5+6: Component Generation ─────────────────────────
            logger.info("Pipeline: Module 5+6 — Generating components")
            component_html: dict[int, str] = {}
            for comp_spec in spec.all_components:
                logger.info(f"  → Generating {comp_spec.type.value} (order={comp_spec.order})")
                html_fragment = await self._registry.generate_component(
                    comp_spec, theme, self._provider, self._config,
                )
                component_html[comp_spec.order] = html_fragment
                logger.debug(f"  → {comp_spec.type.value}: {len(html_fragment)} chars")

            # ── Module 7: HTML Assembly ───────────────────────────────────
            logger.info("Pipeline: Module 7 — Assembling HTML")
            full_html = self._html_builder.build(spec, theme, component_html)
            body_html = self._html_builder.build_body_only(spec, theme, component_html)
            logger.info(f"  → Full HTML: {len(full_html)} chars")

            # ── Module 8+9: Validate + Repair ─────────────────────────────
            logger.info("Pipeline: Module 8+9 — Validating & repairing")
            repaired_body, validation = self._repair_engine.repair(
                body_html, self._validator_chain,
            )

            # If body was repaired, rebuild full HTML
            if repaired_body != body_html:
                logger.info("  → Body HTML was repaired; rebuilding full page")
                # Re-parse repaired body into component map isn't needed;
                # just rebuild with the repaired body directly
                full_html = self._html_builder._wrap_page(spec, theme, repaired_body)
                body_html = repaired_body

            elapsed = time.perf_counter() - start

            # ── Module 10: Evaluation (Sprint 1) ─────────────────────────
            result = PipelineResult(
                html=full_html,
                body_html=body_html,
                spec=spec,
                analysis=analysis,
                plan=plan,
                theme=theme,
                validation=validation,
                elapsed_seconds=elapsed,
                component_count=plan.total_components,
            )
            eval_result = self._evaluator.evaluate(result)
            result.evaluation = eval_result

            logger.info(
                f"Pipeline complete — {plan.total_components} components, "
                f"{len(full_html)} chars, {elapsed:.2f}s — "
                f"validation: {validation.summary()} — "
                f"evaluation: {eval_result.summary()}"
            )

            return result

        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error(f"Pipeline failed after {elapsed:.2f}s: {exc}", exc_info=True)
            return PipelineResult(
                html="",
                body_html="",
                spec=WebsiteSpec(),
                analysis=PromptAnalysisResult(),
                plan=GenerationPlan(website_type=WebsiteSpec().website_type, industry="general", components=[]),
                theme=ResolvedTheme(
                    colors=WebsiteSpec().theme.colors,
                    mode=WebsiteSpec().theme.mode,
                    tone=WebsiteSpec().theme.tone,
                ),
                validation=ValidationReport(),
                elapsed_seconds=elapsed,
                success=False,
                error=str(exc),
            )

    async def run_streaming(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Sprint 6: Real Streaming with status events.

        Yields JSON-encoded status events that the frontend parses for live progress:
          {"type": "status", "stage": "analyzing", "message": "Analyzing prompt..."}
          {"type": "status", "stage": "planning", "message": "Planning 8 components..."}
          {"type": "status", "stage": "generating", "component": "Hero", "progress": "2/8"}
          {"type": "html", "component": "Hero", "html": "<section>...</section>"}
          {"type": "status", "stage": "validating", "message": "Validating HTML..."}
          {"type": "done", "score": 92, "grade": "A", "components": 8}

        The frontend shows:
          Analyzing... → Planning... → Generating Hero... → ... → Validating... → Done ✓
        """
        import json

        start = time.perf_counter()

        # ── Module 1: Analysis ─────────────────────────────────────────────
        yield self._sse_status("analyzing", "Analyzing your prompt...")
        analysis = self._analyzer.analyze(prompt)
        yield self._sse_status(
            "analyzed",
            f"Detected: {analysis.website_type.value} website for {analysis.industry}",
            data={"website_type": analysis.website_type.value, "industry": analysis.industry},
        )

        # ── Module 2: Planning ─────────────────────────────────────────────
        yield self._sse_status("planning", "Planning components...")
        plan = self._planner.plan(analysis)
        yield self._sse_status(
            "planned",
            f"Planning {plan.total_components} components",
            data={"total_components": plan.total_components, "estimated_tokens": plan.estimated_tokens},
        )

        # ── Module 3: Spec ─────────────────────────────────────────────────
        spec = self._spec_builder.build(analysis, plan)

        # ── Module 4: Theme ────────────────────────────────────────────────
        yield self._sse_status("theming", f"Applying {analysis.tone.value} {analysis.theme.value} theme...")
        theme = self._theme_engine.resolve(spec.theme, analysis)

        # ── Module 5+6: Component Generation ───────────────────────────────
        total = len(spec.all_components)
        component_html_map: dict[int, str] = {}

        for i, comp_spec in enumerate(spec.all_components):
            comp_name = comp_spec.type.value
            yield self._sse_status(
                "generating",
                f"Generating {comp_name}...",
                data={"component": comp_name, "progress": f"{i + 1}/{total}"},
            )

            html_fragment = await self._registry.generate_component(
                comp_spec, theme, self._provider, self._config,
            )

            # Quick sanitize
            from ai.repair.engine import RegexRepairStrategy
            from ai.validators.chain import ValidationIssue, Severity
            strategy = RegexRepairStrategy()
            quick_issues = [
                ValidationIssue("quick", Severity.ERROR, "", "strip_code_fences"),
                ValidationIssue("quick", Severity.ERROR, "", "strip_think_blocks"),
                ValidationIssue("quick", Severity.ERROR, "", "strip_dangerous_content"),
            ]
            html_fragment = strategy.repair(html_fragment, quick_issues)

            component_html_map[comp_spec.order] = html_fragment

            # Yield the component HTML
            yield self._sse_html(comp_name, html_fragment, i + 1, total)

        # ── Module 8+9: Validate ───────────────────────────────────────────
        yield self._sse_status("validating", "Validating and optimizing...")
        body_html = self._html_builder.build_body_only(spec, theme, component_html_map)
        repaired_body, validation = self._repair_engine.repair(body_html, self._validator_chain)

        elapsed = time.perf_counter() - start

        # ── Done ───────────────────────────────────────────────────────────
        yield self._sse_done(
            score=validation.score,
            components=total,
            elapsed_seconds=round(elapsed, 2),
        )

    async def regenerate_component(
        self,
        spec: WebsiteSpec,
        theme: ResolvedTheme,
        component_type: str,
        existing_html: dict[int, str],
        instructions: str = "",
    ) -> tuple[str, dict[int, str]]:
        """
        Sprint 7: Incremental Regeneration.

        Instead of regenerating the full website, only regenerate ONE component.
        The rest of the page stays intact.

        Usage:
            new_html, updated_map = await pipeline.regenerate_component(
                spec, theme,
                component_type="Hero",
                existing_html=component_html_map,
                instructions="Make it more dramatic with a split layout",
            )

        Args:
            spec: Existing WebsiteSpec
            theme: Existing ResolvedTheme
            component_type: Which component to regenerate (e.g., "Hero")
            existing_html: Current component HTML map (order → html)
            instructions: Optional additional instructions for regeneration

        Returns:
            Tuple of (full page HTML, updated component HTML map)
        """
        from schemas.generation import ComponentType as CT

        # Find the target component
        target_comp = None
        for comp in spec.all_components:
            if comp.type.value == component_type:
                target_comp = comp
                break

        if not target_comp:
            logger.warning(f"Component type '{component_type}' not found in spec")
            full_html = self._html_builder.build(spec, theme, existing_html)
            return full_html, existing_html

        # If there are additional instructions, inject them into props
        if instructions:
            target_comp.props["_regen_instructions"] = instructions

        logger.info(f"Regenerating component: {component_type}")
        new_html = await self._registry.generate_component(
            target_comp, theme, self._provider, self._config,
        )

        # Sanitize
        from ai.repair.engine import RegexRepairStrategy
        from ai.validators.chain import ValidationIssue, Severity
        strategy = RegexRepairStrategy()
        quick_issues = [
            ValidationIssue("quick", Severity.ERROR, "", "strip_code_fences"),
            ValidationIssue("quick", Severity.ERROR, "", "strip_think_blocks"),
            ValidationIssue("quick", Severity.ERROR, "", "strip_dangerous_content"),
        ]
        new_html = strategy.repair(new_html, quick_issues)

        # Update the map
        updated = dict(existing_html)
        updated[target_comp.order] = new_html

        # Rebuild full page
        full_html = self._html_builder.build(spec, theme, updated)
        return full_html, updated

    # ── SSE Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _sse_status(stage: str, message: str, data: dict | None = None) -> str:
        import json
        event = {"type": "status", "stage": stage, "message": message}
        if data:
            event["data"] = data
        return json.dumps(event)

    @staticmethod
    def _sse_html(component: str, html: str, current: int, total: int) -> str:
        import json
        return json.dumps({
            "type": "html",
            "component": component,
            "html": html,
            "progress": {"current": current, "total": total},
        })

    @staticmethod
    def _sse_done(score: float, components: int, elapsed_seconds: float) -> str:
        import json
        return json.dumps({
            "type": "done",
            "score": round(score, 1),
            "components": components,
            "elapsed_seconds": elapsed_seconds,
        })

