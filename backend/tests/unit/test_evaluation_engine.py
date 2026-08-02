"""
tests/unit/test_evaluation_engine.py — Tests for Phase 5 Quality & Intelligence

Sprint 1: Evaluation Engine (rubric + evaluator)
Sprint 2: Golden Dataset
Sprint 3: Benchmark Runner
Sprint 4: Component Benchmarks
Sprint 5: Prompt Versioning
Sprint 6: Streaming events (structure tests)
Sprint 7: Incremental regeneration (structure tests)
Sprint 9: Performance profiling
"""
import json
import pytest

from evaluation.rubric import (
    DimensionScore,
    EvalDimension,
    EvaluationResult,
    DIMENSION_WEIGHTS,
)
from evaluation.evaluator import (
    WebsiteEvaluator,
    HTMLQualityScorer,
    AccessibilityScorer,
    SEOScorer,
    PerformanceScorer,
    ResponsivenessScorer,
    VisualConsistencyScorer,
    PromptFidelityScorer,
    ComponentQualityScorer,
)
from evaluation.benchmarks import (
    BenchmarkRunner,
    GOLDEN_DATASET,
    GoldenTestCase,
    GoldenTestResult,
    BenchmarkReport,
)
from evaluation.reports import (
    ComponentBenchmarkRunner,
    PromptVersionStore,
    PerformanceProfile,
    StageTimingResult,
)
from schemas.generation import (
    ComponentSpec,
    ComponentType,
    PageSpec,
    PromptAnalysisResult,
    ThemeMode,
    ToneStyle,
    WebsiteSpec,
    WebsiteType,
)


# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 1: RUBRIC
# ══════════════════════════════════════════════════════════════════════════════

class TestRubric:

    def test_dimension_weights_sum_to_one(self):
        total = sum(DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected 1.0"

    def test_all_dimensions_have_weights(self):
        for dim in EvalDimension:
            assert dim in DIMENSION_WEIGHTS, f"Missing weight for {dim.value}"

    def test_grade_calculation(self):
        result = EvaluationResult()
        assert result._to_grade(96) == "A+"
        assert result._to_grade(92) == "A"
        assert result._to_grade(87) == "B+"
        assert result._to_grade(82) == "B"
        assert result._to_grade(72) == "C"
        assert result._to_grade(62) == "D"
        assert result._to_grade(50) == "F"

    def test_overall_calculation(self):
        result = EvaluationResult()
        for dim in EvalDimension:
            result.dimensions[dim] = DimensionScore(
                dimension=dim, score=90.0,
            )
        result.calculate_overall()
        assert result.overall_score == pytest.approx(90.0, abs=0.5)
        assert result.grade == "A"

    def test_to_dict(self):
        result = EvaluationResult()
        for dim in EvalDimension:
            result.dimensions[dim] = DimensionScore(dimension=dim, score=85.0)
        result.calculate_overall()
        d = result.to_dict()
        assert "overall_score" in d
        assert "grade" in d
        assert "dimensions" in d
        assert len(d["dimensions"]) == len(EvalDimension)

    def test_weighted_score(self):
        score = DimensionScore(dimension=EvalDimension.SEO, score=90.0, weight=0.1)
        assert score.weighted_score == 9.0

    def test_summary(self):
        result = EvaluationResult()
        for dim in EvalDimension:
            result.dimensions[dim] = DimensionScore(dimension=dim, score=80.0)
        result.calculate_overall()
        s = result.summary()
        assert "Overall:" in s
        assert "80" in s


# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 1: INDIVIDUAL SCORERS
# ══════════════════════════════════════════════════════════════════════════════

# Sample high-quality HTML for testing
GOOD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="TechNova - AI-powered SaaS platform">
  <title>TechNova</title>
  <style>
    :root {
      --color-primary: #6366f1;
      --color-bg: #020617;
      --font-heading: 'Inter', sans-serif;
    }
  </style>
</head>
<body>
  <nav class="flex items-center justify-between px-6 py-4 md:px-12 lg:px-20">
    <a href="/" class="text-xl font-bold">TechNova</a>
    <div class="hidden md:flex gap-6">
      <a href="#features">Features</a>
      <a href="#pricing">Pricing</a>
    </div>
  </nav>

  <section class="min-h-screen flex items-center justify-center px-6 md:px-12 lg:px-20">
    <div class="max-w-4xl text-center">
      <h1 class="text-4xl md:text-6xl font-bold">Build Faster with AI</h1>
      <p class="mt-6 text-lg opacity-80">Ship products 10x faster with TechNova AI platform.</p>
      <button class="mt-8 px-8 py-3 rounded-xl" aria-label="Get Started">Get Started</button>
    </div>
  </section>

  <section id="features" class="py-20 px-6 md:px-12 lg:px-20">
    <h2 class="text-3xl font-bold text-center">Features</h2>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mt-12 max-w-6xl mx-auto">
      <article class="p-6 rounded-xl" style="background: var(--color-primary)">
        <h3 class="text-xl font-bold">Fast</h3>
        <p>Lightning fast performance.</p>
      </article>
      <article class="p-6 rounded-xl">
        <h3 class="text-xl font-bold">Secure</h3>
        <p>Enterprise-grade security.</p>
      </article>
      <article class="p-6 rounded-xl">
        <h3 class="text-xl font-bold">Smart</h3>
        <p>AI-powered insights.</p>
      </article>
    </div>
  </section>

  <section id="pricing" class="py-20 px-6 md:px-12">
    <h2 class="text-3xl font-bold text-center">Pricing</h2>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mt-12 max-w-5xl mx-auto">
      <div class="p-8 rounded-xl">
        <h3>Starter</h3>
        <p class="text-3xl font-bold">$9</p>
      </div>
      <div class="p-8 rounded-xl">
        <h3>Pro</h3>
        <p class="text-3xl font-bold">$29</p>
      </div>
      <div class="p-8 rounded-xl">
        <h3>Enterprise</h3>
        <p class="text-3xl font-bold">$99</p>
      </div>
    </div>
  </section>

  <footer class="py-12 px-6 md:px-12 text-center">
    <p>© 2024 TechNova. All rights reserved.</p>
    <img src="logo.png" alt="TechNova company logo" loading="lazy">
  </footer>
</body>
</html>"""

BAD_HTML = "```html\n<think>reasoning</think><div>bad</div><script>alert(1)</script>\n```"


class TestHTMLQualityScorer:
    def setup_method(self):
        self.scorer = HTMLQualityScorer()

    def test_good_html_scores_high(self):
        result = self.scorer.score(GOOD_HTML)
        assert result.score >= 80

    def test_bad_html_scores_low(self):
        result = self.scorer.score(BAD_HTML)
        assert result.score < 60

    def test_empty_html_scores_low(self):
        result = self.scorer.score("")
        assert result.score < 60

    def test_code_fences_deduct(self):
        result = self.scorer.score('```html<div>test</div>```')
        assert any("code fences" in d.lower() for d in result.deductions)


class TestAccessibilityScorer:
    def setup_method(self):
        self.scorer = AccessibilityScorer()

    def test_good_html_accessibility(self):
        result = self.scorer.score(GOOD_HTML)
        assert result.score >= 70

    def test_missing_alt_deducts(self):
        html = '<section><img src="test.jpg"></section>'
        result = self.scorer.score(html)
        assert any("alt" in d.lower() for d in result.deductions)


class TestSEOScorer:
    def setup_method(self):
        self.scorer = SEOScorer()

    def test_good_seo(self):
        result = self.scorer.score(GOOD_HTML)
        assert result.score >= 80

    def test_missing_h1(self):
        html = '<section><h2>No H1 here</h2></section>'
        result = self.scorer.score(html)
        assert any("h1" in d.lower() for d in result.deductions)

    def test_multiple_h1(self):
        html = '<h1>First</h1><h1>Second</h1>'
        result = self.scorer.score(html)
        assert any("Multiple" in d for d in result.deductions)


class TestPerformanceScorer:
    def setup_method(self):
        self.scorer = PerformanceScorer()

    def test_compact_html(self):
        result = self.scorer.score(GOOD_HTML)
        assert result.score >= 80

    def test_script_tag_deducts(self):
        html = '<section>ok</section><script>bad()</script>'
        result = self.scorer.score(html)
        assert any("script" in d.lower() for d in result.deductions)


class TestResponsivenessScorer:
    def setup_method(self):
        self.scorer = ResponsivenessScorer()

    def test_responsive_html(self):
        result = self.scorer.score(GOOD_HTML)
        assert result.score >= 70

    def test_no_responsive_classes(self):
        html = '<div class="block"><p>No responsive</p></div>'
        result = self.scorer.score(html)
        assert result.score < 70


class TestVisualConsistencyScorer:
    def setup_method(self):
        self.scorer = VisualConsistencyScorer()

    def test_consistent_design(self):
        result = self.scorer.score(GOOD_HTML)
        assert result.score >= 70

    def test_css_vars_detected(self):
        html = '<div style="color: var(--color-primary)">test</div>'
        result = self.scorer.score(html)
        assert any("custom properties" in d.lower() for d in result.details)


class TestPromptFidelityScorer:
    def setup_method(self):
        self.scorer = PromptFidelityScorer()

    def test_with_analysis(self):
        analysis = PromptAnalysisResult(
            website_type=WebsiteType.SAAS,
            industry="ai",
            brand_name="TechNova",
            requested_components=["Navbar", "Hero"],
        )
        spec = WebsiteSpec(
            website_type=WebsiteType.SAAS,
            pages=[PageSpec(components=[
                ComponentSpec(type=ComponentType.NAVBAR, order=0),
                ComponentSpec(type=ComponentType.HERO, order=1),
            ])],
        )
        result = self.scorer.score(GOOD_HTML, analysis=analysis, spec=spec)
        assert result.score >= 70

    def test_without_analysis(self):
        result = self.scorer.score(GOOD_HTML)
        assert result.score == 50.0  # Fallback


# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 1: FULL EVALUATOR
# ══════════════════════════════════════════════════════════════════════════════

class TestWebsiteEvaluator:

    def test_evaluate_good_html(self):
        evaluator = WebsiteEvaluator()
        # Build a mock PipelineResult
        from ai.pipeline.runner import PipelineResult
        from ai.builders.theme_engine import ResolvedTheme
        from ai.validators.chain import ValidationReport
        from schemas.generation import ColorPalette, GenerationPlan

        result = PipelineResult(
            html=GOOD_HTML,
            body_html=GOOD_HTML,
            spec=WebsiteSpec(
                website_type=WebsiteType.SAAS,
                pages=[PageSpec(components=[
                    ComponentSpec(type=ComponentType.NAVBAR, order=0),
                    ComponentSpec(type=ComponentType.HERO, order=1),
                ])],
            ),
            analysis=PromptAnalysisResult(
                website_type=WebsiteType.SAAS,
                industry="ai",
                brand_name="TechNova",
                requested_components=["Navbar", "Hero"],
            ),
            plan=GenerationPlan(website_type=WebsiteType.SAAS, industry="ai", components=[]),
            theme=ResolvedTheme(colors=ColorPalette(), mode=ThemeMode.DARK, tone=ToneStyle.MODERN),
            validation=ValidationReport(),
        )

        eval_result = evaluator.evaluate(result)
        assert eval_result.overall_score > 60
        assert eval_result.grade in ("A+", "A", "B+", "B", "C")
        assert len(eval_result.dimensions) == 8

    def test_evaluate_html_directly(self):
        evaluator = WebsiteEvaluator()
        result = evaluator.evaluate_html(GOOD_HTML)
        assert result.overall_score > 50
        assert result.grade != "F"

    def test_evaluate_bad_html(self):
        evaluator = WebsiteEvaluator()
        result = evaluator.evaluate_html(BAD_HTML)
        assert result.overall_score < 60
        assert result.grade in ("D", "F")


# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 2: GOLDEN DATASET
# ══════════════════════════════════════════════════════════════════════════════

class TestGoldenDataset:

    def test_dataset_has_minimum_cases(self):
        assert len(GOLDEN_DATASET) >= 10

    def test_all_cases_have_required_fields(self):
        for case in GOLDEN_DATASET:
            assert case.id
            assert case.prompt
            assert case.expected_type
            assert len(case.expected_components) >= 2
            assert case.min_score >= 50

    def test_unique_ids(self):
        ids = [c.id for c in GOLDEN_DATASET]
        assert len(ids) == len(set(ids)), "Duplicate golden dataset IDs"

    def test_covers_multiple_types(self):
        types = set(c.expected_type for c in GOLDEN_DATASET)
        assert len(types) >= 5, f"Only covers {len(types)} types"

    def test_analyzer_benchmark_runs(self):
        """Run the deterministic benchmark (no LLM needed)."""
        runner = BenchmarkRunner()
        report = runner.run_analyzer_benchmark()
        assert report.total_tests >= 10
        assert report.passed > 0
        assert report.average_score > 0
        assert report.summary()

    def test_benchmark_report_to_dict(self):
        runner = BenchmarkRunner()
        report = runner.run_analyzer_benchmark()
        d = report.to_dict()
        assert "total" in d
        assert "passed" in d
        assert "results" in d
        assert len(d["results"]) == report.total_tests


# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 4: COMPONENT BENCHMARKS
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentBenchmarks:

    def test_component_benchmark_runs(self):
        runner = ComponentBenchmarkRunner()
        report = runner.run()
        assert len(report.results) >= 20
        assert report.average_score > 0
        assert report.strongest_component
        assert report.weakest_component

    def test_component_benchmark_summary(self):
        runner = ComponentBenchmarkRunner()
        report = runner.run()
        summary = report.summary()
        assert "Component Benchmark Report" in summary
        assert "Strongest" in summary

    def test_all_generators_benchmarked(self):
        runner = ComponentBenchmarkRunner()
        report = runner.run()
        # Check key components
        assert "Navbar" in report.results
        assert "Hero" in report.results
        assert "Footer" in report.results
        assert "Pricing" in report.results


# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 5: PROMPT VERSIONING
# ══════════════════════════════════════════════════════════════════════════════

class TestPromptVersioning:

    def test_register_and_retrieve(self):
        store = PromptVersionStore()
        store.register("Hero", "1.0.0", "Generate a hero section...")
        store.register("Hero", "1.1.0", "Generate a PREMIUM hero section...")

        versions = store.get_versions("Hero")
        assert len(versions) == 2
        assert versions[0].version == "1.0.0"
        assert versions[1].version == "1.1.0"

    def test_get_latest(self):
        store = PromptVersionStore()
        store.register("Hero", "1.0.0", "v1")
        store.register("Hero", "2.0.0", "v2")
        latest = store.get_latest("Hero")
        assert latest is not None
        assert latest.version == "2.0.0"

    def test_get_specific_version(self):
        store = PromptVersionStore()
        store.register("Hero", "1.0.0", "v1 template")
        pv = store.get_version("Hero", "1.0.0")
        assert pv is not None
        assert pv.template == "v1 template"

    def test_missing_version(self):
        store = PromptVersionStore()
        assert store.get_version("Hero", "99.0.0") is None
        assert store.get_latest("NonExistent") is None

    def test_all_component_types(self):
        store = PromptVersionStore()
        store.register("Hero", "1.0.0", "a")
        store.register("Pricing", "1.0.0", "b")
        assert sorted(store.all_component_types) == ["Hero", "Pricing"]

    def test_total_versions(self):
        store = PromptVersionStore()
        store.register("Hero", "1.0.0", "a")
        store.register("Hero", "1.1.0", "b")
        store.register("Footer", "1.0.0", "c")
        assert store.total_versions == 3


# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 6: STREAMING EVENTS (structure tests)
# ══════════════════════════════════════════════════════════════════════════════

class TestStreamingEvents:

    def test_sse_status_format(self):
        from ai.pipeline.runner import GenerationPipelineV1
        result = GenerationPipelineV1._sse_status("analyzing", "Analyzing prompt...")
        parsed = json.loads(result)
        assert parsed["type"] == "status"
        assert parsed["stage"] == "analyzing"
        assert "message" in parsed

    def test_sse_html_format(self):
        from ai.pipeline.runner import GenerationPipelineV1
        result = GenerationPipelineV1._sse_html("Hero", "<section>Test</section>", 1, 8)
        parsed = json.loads(result)
        assert parsed["type"] == "html"
        assert parsed["component"] == "Hero"
        assert parsed["html"] == "<section>Test</section>"
        assert parsed["progress"]["current"] == 1
        assert parsed["progress"]["total"] == 8

    def test_sse_done_format(self):
        from ai.pipeline.runner import GenerationPipelineV1
        result = GenerationPipelineV1._sse_done(92.5, 8, 3.14)
        parsed = json.loads(result)
        assert parsed["type"] == "done"
        assert parsed["score"] == 92.5
        assert parsed["components"] == 8

    def test_sse_status_with_data(self):
        from ai.pipeline.runner import GenerationPipelineV1
        result = GenerationPipelineV1._sse_status(
            "analyzed", "Detected SaaS", data={"website_type": "saas"}
        )
        parsed = json.loads(result)
        assert parsed["data"]["website_type"] == "saas"


# ══════════════════════════════════════════════════════════════════════════════
# SPRINT 9: PERFORMANCE PROFILER
# ══════════════════════════════════════════════════════════════════════════════

class TestPerformanceProfile:

    def test_profile_calculation(self):
        profile = PerformanceProfile(stages=[
            StageTimingResult(stage="Analyzer", elapsed_ms=120),
            StageTimingResult(stage="Planner", elapsed_ms=30),
            StageTimingResult(stage="Generators", elapsed_ms=8000),
            StageTimingResult(stage="Validator", elapsed_ms=90),
            StageTimingResult(stage="Repair", elapsed_ms=1300),
        ])
        profile.calculate()
        assert profile.total_ms == pytest.approx(9540.0)
        assert profile.bottleneck == "Generators"
        assert profile.bottleneck_ms == 8000

    def test_profile_percentages(self):
        profile = PerformanceProfile(stages=[
            StageTimingResult(stage="A", elapsed_ms=50),
            StageTimingResult(stage="B", elapsed_ms=50),
        ])
        profile.calculate()
        assert profile.stages[0].percentage == pytest.approx(50.0)

    def test_profile_summary(self):
        profile = PerformanceProfile(stages=[
            StageTimingResult(stage="Analyzer", elapsed_ms=100),
        ])
        profile.calculate()
        summary = profile.summary()
        assert "Analyzer" in summary
        assert "Bottleneck" in summary
