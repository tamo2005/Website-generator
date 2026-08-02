"""
evaluation/benchmarks.py — Sprint 2 & 3: Golden Dataset + Benchmark Runner

Golden Dataset: A curated set of prompts with EXPECTED outputs.
  → Run after every code change.
  → If scores drop, you know you broke something.

Benchmark Runner: Compare providers/models scientifically.
  → Same prompt → different models → evaluation → winner.

Usage:
    runner = BenchmarkRunner()
    report = await runner.run_golden_dataset()
    report = await runner.compare_providers(prompt, providers)
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from evaluation.evaluator import WebsiteEvaluator
from evaluation.rubric import EvaluationResult
from schemas.generation import ComponentType, WebsiteType

if TYPE_CHECKING:
    from ai.pipeline.runner import GenerationPipelineV1, PipelineResult

logger = logging.getLogger("ai-site-gen")


# ══════════════════════════════════════════════════════════════════════════════
# GOLDEN DATASET
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class GoldenTestCase:
    """A single test case in the golden dataset."""
    id: str
    prompt: str
    expected_type: WebsiteType
    expected_components: list[str]
    expected_industry: str = "general"
    min_score: float = 70.0            # Minimum acceptable overall score
    tags: list[str] = field(default_factory=list)


@dataclass
class GoldenTestResult:
    """Result of running a single golden test case."""
    test_case: GoldenTestCase
    passed: bool
    evaluation: Optional[EvaluationResult] = None
    actual_type: Optional[WebsiteType] = None
    actual_components: list[str] = field(default_factory=list)
    missing_components: list[str] = field(default_factory=list)
    extra_components: list[str] = field(default_factory=list)
    error: Optional[str] = None
    elapsed_ms: float = 0.0


# The Golden Dataset — curated prompts with expected outputs
GOLDEN_DATASET: list[GoldenTestCase] = [
    GoldenTestCase(
        id="golden-001",
        prompt="Create a SaaS landing page for an AI startup called TechNova with pricing and FAQ",
        expected_type=WebsiteType.SAAS,
        expected_components=["Navbar", "Hero", "Features", "Pricing", "FAQ", "Footer"],
        expected_industry="ai",
        min_score=75.0,
        tags=["saas", "ai", "pricing"],
    ),
    GoldenTestCase(
        id="golden-002",
        prompt="Build a restaurant website with a menu and reservation system for a cafe called Brew & Bite",
        expected_type=WebsiteType.RESTAURANT,
        expected_components=["Navbar", "Hero", "Menu", "Reservation", "Footer"],
        expected_industry="food",
        min_score=70.0,
        tags=["restaurant", "food"],
    ),
    GoldenTestCase(
        id="golden-003",
        prompt="Create a developer portfolio with projects, skills, and contact form",
        expected_type=WebsiteType.PORTFOLIO,
        expected_components=["Navbar", "Hero", "Projects", "Skills", "Contact", "Footer"],
        expected_industry="technology",
        min_score=70.0,
        tags=["portfolio", "developer"],
    ),
    GoldenTestCase(
        id="golden-004",
        prompt="Build a dark theme e-commerce landing page with testimonials and a gallery",
        expected_type=WebsiteType.ECOMMERCE,
        expected_components=["Navbar", "Hero", "Gallery", "Testimonials", "Footer"],
        expected_industry="general",
        min_score=70.0,
        tags=["ecommerce", "dark"],
    ),
    GoldenTestCase(
        id="golden-005",
        prompt="Create a blog with articles and newsletter subscription",
        expected_type=WebsiteType.BLOG,
        expected_components=["Navbar", "Hero", "BlogPosts", "Newsletter", "Footer"],
        expected_industry="general",
        min_score=70.0,
        tags=["blog", "newsletter"],
    ),
    GoldenTestCase(
        id="golden-006",
        prompt="Build a creative agency website with services, team, and case studies",
        expected_type=WebsiteType.AGENCY,
        expected_components=["Navbar", "Hero", "Services", "Team", "Projects", "Footer"],
        expected_industry="marketing",
        min_score=70.0,
        tags=["agency", "creative"],
    ),
    GoldenTestCase(
        id="golden-007",
        prompt="Create a minimal, light theme startup landing page with stats and how it works section",
        expected_type=WebsiteType.STARTUP,
        expected_components=["Navbar", "Hero", "Stats", "HowItWorks", "Footer"],
        expected_industry="general",
        min_score=70.0,
        tags=["startup", "light", "minimal"],
    ),
    GoldenTestCase(
        id="golden-008",
        prompt="Build a neon-styled SaaS dashboard page with pricing, FAQ, and testimonials",
        expected_type=WebsiteType.DASHBOARD,
        expected_components=["Navbar", "Hero", "Pricing", "FAQ", "Testimonials", "Footer"],
        expected_industry="general",
        min_score=70.0,
        tags=["dashboard", "neon", "saas"],
    ),
    GoldenTestCase(
        id="golden-009",
        prompt="Build a corporate business website with about us, services, team, and contact",
        expected_type=WebsiteType.BUSINESS,
        expected_components=["Navbar", "Hero", "About", "Services", "Team", "Contact", "Footer"],
        expected_industry="general",
        min_score=70.0,
        tags=["business", "corporate"],
    ),
    GoldenTestCase(
        id="golden-010",
        prompt="Portfolio website",
        expected_type=WebsiteType.PORTFOLIO,
        expected_components=["Navbar", "Hero", "Footer"],
        expected_industry="general",
        min_score=65.0,
        tags=["simple", "portfolio"],
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# BENCHMARK REPORT
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class BenchmarkReport:
    """Aggregate report from a benchmark run."""
    test_results: list[GoldenTestResult] = field(default_factory=list)
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    average_score: float = 0.0
    min_score: float = 100.0
    max_score: float = 0.0
    elapsed_seconds: float = 0.0

    def calculate(self) -> None:
        self.total_tests = len(self.test_results)
        self.passed = sum(1 for r in self.test_results if r.passed)
        self.failed = self.total_tests - self.passed
        scores = [r.evaluation.overall_score for r in self.test_results if r.evaluation]
        if scores:
            self.average_score = sum(scores) / len(scores)
            self.min_score = min(scores)
            self.max_score = max(scores)

    def summary(self) -> str:
        return (
            f"Benchmark: {self.passed}/{self.total_tests} passed | "
            f"Avg: {self.average_score:.1f} | "
            f"Min: {self.min_score:.1f} | Max: {self.max_score:.1f} | "
            f"Time: {self.elapsed_seconds:.1f}s"
        )

    def to_dict(self) -> dict:
        return {
            "total": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "average_score": round(self.average_score, 1),
            "min_score": round(self.min_score, 1),
            "max_score": round(self.max_score, 1),
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "results": [
                {
                    "id": r.test_case.id,
                    "prompt": r.test_case.prompt[:80],
                    "passed": r.passed,
                    "score": round(r.evaluation.overall_score, 1) if r.evaluation else 0,
                    "grade": r.evaluation.grade if r.evaluation else "?",
                    "missing": r.missing_components,
                    "error": r.error,
                }
                for r in self.test_results
            ],
        }


# ══════════════════════════════════════════════════════════════════════════════
# BENCHMARK RUNNER
# ══════════════════════════════════════════════════════════════════════════════

class BenchmarkRunner:
    """
    Sprint 2+3: Golden dataset testing + provider comparison.

    Usage:
        runner = BenchmarkRunner(pipeline)
        report = await runner.run_golden_dataset()

        # Sprint 3: Compare providers
        comparison = await runner.compare_providers(
            "Build a SaaS landing page",
            [openrouter_pipeline, gemini_pipeline]
        )
    """

    def __init__(self, evaluator: Optional[WebsiteEvaluator] = None) -> None:
        self._evaluator = evaluator or WebsiteEvaluator()

    def run_analyzer_benchmark(self) -> BenchmarkReport:
        """
        Run the golden dataset against the PromptAnalyzer ONLY (no LLM).
        Tests Modules 1-3 deterministically.
        """
        from ai.planner.analyzer import PromptAnalyzer
        from ai.planner.planner import AIPlanner
        from ai.planner.spec_builder import SpecBuilder
        from ai.builders.theme_engine import ThemeEngine
        from ai.builders.html_builder import HTMLBuilder
        from ai.registry.generators.all_generators import create_default_registry

        analyzer = PromptAnalyzer()
        planner = AIPlanner()
        spec_builder = SpecBuilder()
        theme_engine = ThemeEngine()
        html_builder = HTMLBuilder()

        report = BenchmarkReport()
        start = time.perf_counter()

        for test_case in GOLDEN_DATASET:
            try:
                t0 = time.perf_counter()

                # Run Modules 1-3
                analysis = analyzer.analyze(test_case.prompt)
                plan = planner.plan(analysis)
                spec = spec_builder.build(analysis, plan)
                theme = theme_engine.resolve(spec.theme, analysis)

                # Generate fallback HTML (no LLM)
                registry = create_default_registry()
                component_html = {}
                for comp in spec.all_components:
                    gen = registry.get(comp.type)
                    if gen:
                        component_html[comp.order] = gen._fallback_html(comp, theme)
                    else:
                        component_html[comp.order] = ""

                html = html_builder.build(spec, theme, component_html)

                # Evaluate
                eval_result = self._evaluator.evaluate_html(html, analysis, spec)

                # Check expectations
                actual_components = [c.type.value for c in spec.all_components]
                missing = [c for c in test_case.expected_components if c not in actual_components]
                extra = [c for c in actual_components if c not in test_case.expected_components]

                passed = (
                    eval_result.overall_score >= test_case.min_score
                    and len(missing) == 0
                )

                result = GoldenTestResult(
                    test_case=test_case,
                    passed=passed,
                    evaluation=eval_result,
                    actual_type=analysis.website_type,
                    actual_components=actual_components,
                    missing_components=missing,
                    extra_components=extra,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                )

            except Exception as exc:
                result = GoldenTestResult(
                    test_case=test_case,
                    passed=False,
                    error=str(exc),
                )

            report.test_results.append(result)

        report.elapsed_seconds = time.perf_counter() - start
        report.calculate()
        logger.info(f"Analyzer benchmark: {report.summary()}")
        return report

    async def run_golden_dataset(
        self,
        pipeline: "GenerationPipelineV1",
    ) -> BenchmarkReport:
        """
        Run full golden dataset with LLM generation.
        Expensive — use for CI/nightly builds.
        """
        report = BenchmarkReport()
        start = time.perf_counter()

        for test_case in GOLDEN_DATASET:
            try:
                t0 = time.perf_counter()
                pipeline_result = await pipeline.run(test_case.prompt)

                eval_result = self._evaluator.evaluate(pipeline_result)

                actual_components = pipeline_result.spec.component_types
                missing = [c for c in test_case.expected_components if c not in actual_components]

                passed = (
                    eval_result.overall_score >= test_case.min_score
                    and len(missing) == 0
                    and pipeline_result.success
                )

                result = GoldenTestResult(
                    test_case=test_case,
                    passed=passed,
                    evaluation=eval_result,
                    actual_type=pipeline_result.analysis.website_type,
                    actual_components=actual_components,
                    missing_components=missing,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                )
            except Exception as exc:
                result = GoldenTestResult(
                    test_case=test_case,
                    passed=False,
                    error=str(exc),
                )

            report.test_results.append(result)

        report.elapsed_seconds = time.perf_counter() - start
        report.calculate()
        return report


# ══════════════════════════════════════════════════════════════════════════════
# PROVIDER COMPARISON (Sprint 3)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ProviderComparisonResult:
    """Results from comparing multiple providers on the same prompt."""
    prompt: str
    results: dict[str, EvaluationResult] = field(default_factory=dict)  # provider_name → eval
    winner: str = ""
    winner_score: float = 0.0

    def determine_winner(self) -> None:
        if not self.results:
            return
        best = max(self.results.items(), key=lambda x: x[1].overall_score)
        self.winner = best[0]
        self.winner_score = best[1].overall_score

    def summary(self) -> str:
        lines = [f"Prompt: {self.prompt[:60]}..."]
        for name, eval_r in sorted(self.results.items(), key=lambda x: -x[1].overall_score):
            marker = " 🏆" if name == self.winner else ""
            lines.append(f"  {name}: {eval_r.overall_score:.0f} ({eval_r.grade}){marker}")
        return "\n".join(lines)
