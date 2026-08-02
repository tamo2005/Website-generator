"""
evaluation/reports.py — Sprint 4 & 5: Component Benchmarks + Prompt Versioning

Sprint 4: Score each component generator individually.
Sprint 5: Track prompt versions and compare performance.

Architecture:
  Component Benchmark:
    Generator → 10 prompts → Fallback HTML → Score → Average
    Now you know which generators produce the best output.

  Prompt Versioning:
    Prompt v1 → Generation → Score: 78
    Prompt v2 → Generation → Score: 85
    Answer: "Did prompt v7 outperform v6?"
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from evaluation.evaluator import WebsiteEvaluator
from evaluation.rubric import EvaluationResult
from schemas.generation import (
    ComponentSpec,
    ComponentType,
    PromptAnalysisResult,
    WebsiteType,
)

logger = logging.getLogger("ai-site-gen")


# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 4: COMPONENT BENCHMARK
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ComponentBenchmarkResult:
    """Score for a single component type across multiple prompts."""
    component_type: str
    prompts_tested: int = 0
    average_html_size: float = 0.0
    has_semantic_tags: bool = False
    has_responsive_classes: bool = False
    has_interactive_elements: bool = False
    average_generation_ms: float = 0.0
    issues: list[str] = field(default_factory=list)
    score: float = 0.0   # 0-100


@dataclass
class ComponentBenchmarkReport:
    """Full report of all component benchmarks."""
    results: dict[str, ComponentBenchmarkResult] = field(default_factory=dict)
    average_score: float = 0.0
    weakest_component: str = ""
    strongest_component: str = ""
    elapsed_seconds: float = 0.0

    def calculate(self) -> None:
        if not self.results:
            return
        scores = {k: v.score for k, v in self.results.items()}
        self.average_score = sum(scores.values()) / len(scores)
        self.weakest_component = min(scores, key=scores.get)  # type: ignore
        self.strongest_component = max(scores, key=scores.get)  # type: ignore

    def summary(self) -> str:
        lines = ["Component Benchmark Report:"]
        for name, r in sorted(self.results.items(), key=lambda x: -x[1].score):
            lines.append(f"  {name:20s} → {r.score:5.1f}/100  ({r.average_html_size:.0f} chars)")
        lines.append(f"\n  Strongest: {self.strongest_component}")
        lines.append(f"  Weakest:   {self.weakest_component}")
        lines.append(f"  Average:   {self.average_score:.1f}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "average": round(self.average_score, 1),
            "strongest": self.strongest_component,
            "weakest": self.weakest_component,
            "components": {
                name: {
                    "score": round(r.score, 1),
                    "html_size": round(r.average_html_size),
                    "semantic": r.has_semantic_tags,
                    "responsive": r.has_responsive_classes,
                    "issues": r.issues,
                }
                for name, r in self.results.items()
            },
        }


class ComponentBenchmarkRunner:
    """
    Sprint 4: Benchmark each component generator using fallback HTML.

    Tests the quality of fallback output (no LLM needed).
    """

    # Test prompts for industry context
    INDUSTRY_CONTEXTS = [
        PromptAnalysisResult(industry="ai", brand_name="TechNova", website_type=WebsiteType.SAAS),
        PromptAnalysisResult(industry="food", brand_name="Brew & Bite", website_type=WebsiteType.RESTAURANT),
        PromptAnalysisResult(industry="technology", brand_name="DevStudio", website_type=WebsiteType.PORTFOLIO),
        PromptAnalysisResult(industry="finance", brand_name="WealthFlow", website_type=WebsiteType.BUSINESS),
        PromptAnalysisResult(industry="health", brand_name="VitalCare", website_type=WebsiteType.STARTUP),
    ]

    def run(self) -> ComponentBenchmarkReport:
        """Benchmark all component generators using fallback HTML."""
        import re
        from ai.builders.theme_engine import ThemeEngine, ResolvedTheme
        from ai.registry.generators.all_generators import create_default_registry
        from ai.planner.spec_builder import _default_props

        registry = create_default_registry()
        theme_engine = ThemeEngine()
        report = ComponentBenchmarkReport()
        start = time.perf_counter()

        for comp_type in ComponentType:
            gen = registry.get(comp_type)
            if not gen:
                continue

            result = ComponentBenchmarkResult(component_type=comp_type.value)
            html_sizes = []
            scores = []

            for ctx in self.INDUSTRY_CONTEXTS:
                theme_spec = __import__('schemas.generation', fromlist=['ThemeSpec']).ThemeSpec()
                theme = theme_engine.resolve(theme_spec, ctx)
                props = _default_props(comp_type, ctx)
                spec = ComponentSpec(type=comp_type, order=0, props=props)

                t0 = time.perf_counter()
                fallback = gen._fallback_html(spec, theme)
                gen_ms = (time.perf_counter() - t0) * 1000

                html_sizes.append(len(fallback))

                # Score the fallback
                comp_score = 50.0  # Base for fallback

                # Check semantic tags
                if any(tag in fallback.lower() for tag in ["<nav", "<section", "<footer", "<article"]):
                    comp_score += 10
                    result.has_semantic_tags = True

                # Check responsive classes
                if any(p in fallback for p in ["md:", "lg:", "sm:"]):
                    comp_score += 10
                    result.has_responsive_classes = True

                # Check for meaningful content (not empty)
                text_content = re.sub(r"<[^>]+>", "", fallback).strip()
                if len(text_content) > 20:
                    comp_score += 10
                else:
                    result.issues.append("Sparse text content")

                # Check for inline styles (theme compliance)
                if "style=" in fallback:
                    comp_score += 5  # Uses theme colors

                # Check for interactive elements
                if any(tag in fallback for tag in ["<a ", "<button", "<input", "<textarea"]):
                    comp_score += 5
                    result.has_interactive_elements = True

                # Check for proper class usage
                if 'class="' in fallback:
                    comp_score += 10

                scores.append(min(100, comp_score))

            result.prompts_tested = len(self.INDUSTRY_CONTEXTS)
            result.average_html_size = sum(html_sizes) / len(html_sizes) if html_sizes else 0
            result.score = sum(scores) / len(scores) if scores else 0
            result.average_generation_ms = 0.1  # Fallback is instant

            report.results[comp_type.value] = result

        report.elapsed_seconds = time.perf_counter() - start
        report.calculate()
        logger.info(f"Component benchmark: avg={report.average_score:.1f} strongest={report.strongest_component} weakest={report.weakest_component}")
        return report


# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 5: PROMPT VERSIONING
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PromptVersion:
    """A versioned prompt template."""
    version: str                    # e.g., "1.0.0", "1.1.0"
    component_type: str             # e.g., "Hero", "system", "Pricing"
    template: str                   # The actual prompt template
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""


@dataclass
class PromptVersionResult:
    """Result from running a prompt version."""
    version: str
    score: float
    grade: str
    evaluation: Optional[EvaluationResult] = None
    elapsed_ms: float = 0.0


@dataclass
class PromptVersionComparison:
    """Compare two prompt versions."""
    component_type: str
    version_a: PromptVersionResult
    version_b: PromptVersionResult
    winner: str = ""
    improvement: float = 0.0

    def determine_winner(self) -> None:
        if self.version_a.score >= self.version_b.score:
            self.winner = self.version_a.version
            self.improvement = self.version_a.score - self.version_b.score
        else:
            self.winner = self.version_b.version
            self.improvement = self.version_b.score - self.version_a.score

    def summary(self) -> str:
        return (
            f"{self.component_type} prompt comparison:\n"
            f"  v{self.version_a.version}: {self.version_a.score:.1f} ({self.version_a.grade})\n"
            f"  v{self.version_b.version}: {self.version_b.score:.1f} ({self.version_b.grade})\n"
            f"  Winner: v{self.winner} (+{self.improvement:.1f} points)"
        )


class PromptVersionStore:
    """
    Sprint 5: In-memory prompt version store.

    Tracks prompt templates by component type + version.
    Future: persist to database.

    Usage:
        store = PromptVersionStore()
        store.register("Hero", "1.0.0", "Generate a hero section...")
        store.register("Hero", "1.1.0", "Generate a PREMIUM hero section...")

        history = store.get_versions("Hero")
        latest = store.get_latest("Hero")
    """

    def __init__(self) -> None:
        self._versions: dict[str, list[PromptVersion]] = {}

    def register(
        self,
        component_type: str,
        version: str,
        template: str,
        notes: str = "",
    ) -> PromptVersion:
        """Register a new prompt version."""
        pv = PromptVersion(
            version=version,
            component_type=component_type,
            template=template,
            notes=notes,
        )
        if component_type not in self._versions:
            self._versions[component_type] = []
        self._versions[component_type].append(pv)
        logger.debug(f"Registered prompt v{version} for {component_type}")
        return pv

    def get_versions(self, component_type: str) -> list[PromptVersion]:
        """Get all versions for a component type, ordered by version."""
        versions = self._versions.get(component_type, [])
        return sorted(versions, key=lambda v: v.version)

    def get_latest(self, component_type: str) -> Optional[PromptVersion]:
        """Get the latest prompt version for a component type."""
        versions = self.get_versions(component_type)
        return versions[-1] if versions else None

    def get_version(self, component_type: str, version: str) -> Optional[PromptVersion]:
        """Get a specific version."""
        for pv in self._versions.get(component_type, []):
            if pv.version == version:
                return pv
        return None

    @property
    def all_component_types(self) -> list[str]:
        return list(self._versions.keys())

    @property
    def total_versions(self) -> int:
        return sum(len(v) for v in self._versions.values())


# ══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE PROFILER (Sprint 9)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class StageTimingResult:
    """Timing for a single pipeline stage."""
    stage: str
    elapsed_ms: float
    percentage: float = 0.0


@dataclass
class PerformanceProfile:
    """Performance profile of a pipeline run."""
    stages: list[StageTimingResult] = field(default_factory=list)
    total_ms: float = 0.0
    bottleneck: str = ""
    bottleneck_ms: float = 0.0

    def calculate(self) -> None:
        if not self.stages:
            return
        self.total_ms = sum(s.elapsed_ms for s in self.stages)
        for stage in self.stages:
            stage.percentage = (stage.elapsed_ms / self.total_ms * 100) if self.total_ms > 0 else 0
        slowest = max(self.stages, key=lambda s: s.elapsed_ms)
        self.bottleneck = slowest.stage
        self.bottleneck_ms = slowest.elapsed_ms

    def summary(self) -> str:
        lines = ["Pipeline Performance Profile:"]
        for s in sorted(self.stages, key=lambda x: -x.elapsed_ms):
            bar = "█" * int(s.percentage / 2)
            lines.append(f"  {s.stage:20s} {s.elapsed_ms:8.1f} ms  {s.percentage:5.1f}%  {bar}")
        lines.append(f"\n  Total: {self.total_ms:.1f} ms | Bottleneck: {self.bottleneck} ({self.bottleneck_ms:.1f} ms)")
        return "\n".join(lines)
