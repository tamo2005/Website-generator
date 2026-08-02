"""
evaluation/evaluator.py — Website Quality Evaluator

Scores generated HTML across 8 dimensions.
Every generation becomes MEASURABLE.

Input: PipelineResult (HTML + spec + analysis + validation)
Output: EvaluationResult (8 dimension scores + overall + grade)

Architecture:
  PipelineResult
    ↓
  Evaluator
    ↓
  HTMLQualityScorer → AccessibilityScorer → SEOScorer → ...
    ↓
  EvaluationResult { overall: 92, grade: "A", seo: 96, ... }

Usage:
    evaluator = WebsiteEvaluator()
    result = evaluator.evaluate(pipeline_result)
    print(result.summary())  # Overall: 92 (A) | html=95 | a11y=89 | seo=96 | ...
"""
from __future__ import annotations

import logging
import re
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from evaluation.rubric import (
    DimensionScore,
    EvalDimension,
    EvaluationResult,
)

if TYPE_CHECKING:
    from ai.pipeline.runner import PipelineResult
    from schemas.generation import PromptAnalysisResult, WebsiteSpec

logger = logging.getLogger("ai-site-gen")


# ══════════════════════════════════════════════════════════════════════════════
# BASE SCORER
# ══════════════════════════════════════════════════════════════════════════════

class BaseDimensionScorer(ABC):
    """Abstract scorer for a single evaluation dimension."""
    dimension: EvalDimension

    @abstractmethod
    def score(self, html: str, **kwargs) -> DimensionScore:
        ...


# ══════════════════════════════════════════════════════════════════════════════
# HTML QUALITY SCORER
# ══════════════════════════════════════════════════════════════════════════════

class HTMLQualityScorer(BaseDimensionScorer):
    dimension = EvalDimension.HTML_QUALITY

    def score(self, html: str, **kwargs) -> DimensionScore:
        score = 100.0
        details = []
        deductions = []

        # 1. Check starts with valid HTML
        stripped = html.strip()
        if stripped and stripped[0] == "<":
            details.append("Starts with valid HTML tag")
        else:
            score -= 15
            deductions.append("Does not start with HTML tag (-15)")

        # 2. Check for code fences
        if "```" in html:
            score -= 20
            deductions.append("Contains markdown code fences (-20)")

        # 3. Check for think blocks
        if "<think>" in html.lower():
            score -= 20
            deductions.append("Contains LLM think blocks (-20)")

        # 4. Semantic HTML usage
        semantic_tags = ["<nav", "<main", "<section", "<article", "<header", "<footer", "<aside"]
        used = sum(1 for tag in semantic_tags if tag in html.lower())
        if used >= 4:
            details.append(f"Good semantic HTML usage ({used} semantic tags)")
        elif used >= 2:
            score -= 5
            deductions.append(f"Limited semantic tags ({used}/4+) (-5)")
        else:
            score -= 15
            deductions.append(f"Poor semantic HTML ({used} semantic tags) (-15)")

        # 5. Tag closure balance
        for tag in ["section", "div", "nav", "footer"]:
            opens = len(re.findall(rf"<{tag}\b", html, re.I))
            closes = len(re.findall(rf"</{tag}>", html, re.I))
            if opens != closes:
                score -= 5
                deductions.append(f"Unclosed <{tag}> tags: {opens} opened, {closes} closed (-5)")

        # 6. Content length check
        if len(html) < 500:
            score -= 15
            deductions.append(f"HTML too short ({len(html)} chars) (-15)")
        elif len(html) > 200_000:
            score -= 10
            deductions.append(f"HTML excessively large ({len(html)} chars) (-10)")
        else:
            details.append(f"Reasonable HTML size ({len(html):,} chars)")

        return DimensionScore(
            dimension=self.dimension,
            score=max(0, score),
            details=details,
            deductions=deductions,
        )


# ══════════════════════════════════════════════════════════════════════════════
# ACCESSIBILITY SCORER
# ══════════════════════════════════════════════════════════════════════════════

class AccessibilityScorer(BaseDimensionScorer):
    dimension = EvalDimension.ACCESSIBILITY

    def score(self, html: str, **kwargs) -> DimensionScore:
        score = 100.0
        details = []
        deductions = []

        # 1. Landmark regions
        has_nav = "<nav" in html.lower()
        has_main = "<main" in html.lower()
        has_footer = "<footer" in html.lower()

        landmarks = sum([has_nav, has_main, has_footer])
        if landmarks >= 2:
            details.append(f"Good landmark usage ({landmarks}/3)")
        else:
            score -= 10
            deductions.append(f"Missing landmarks ({landmarks}/3) (-10)")

        # 2. Alt text on images
        imgs = re.findall(r"<img\b[^>]*>", html, re.I)
        imgs_no_alt = [img for img in imgs if "alt=" not in img.lower()]
        if imgs and not imgs_no_alt:
            details.append(f"All {len(imgs)} images have alt text")
        elif imgs_no_alt:
            penalty = min(len(imgs_no_alt) * 5, 20)
            score -= penalty
            deductions.append(f"{len(imgs_no_alt)}/{len(imgs)} images missing alt text (-{penalty})")

        # 3. Form labels
        inputs = re.findall(r"<input\b[^>]*>", html, re.I)
        has_labels = "<label" in html.lower()
        has_aria = "aria-label" in html.lower()
        if inputs and not has_labels and not has_aria:
            score -= 10
            deductions.append("Form inputs without labels or aria-labels (-10)")
        elif inputs:
            details.append("Form inputs have labels/aria-labels")

        # 4. Heading hierarchy
        headings = re.findall(r"<h([1-6])\b", html, re.I)
        if headings:
            levels = [int(h) for h in headings]
            if levels[0] != 1:
                score -= 5
                deductions.append("First heading is not h1 (-5)")
            # Check for skipped levels
            for i in range(1, len(levels)):
                if levels[i] > levels[i-1] + 1:
                    score -= 3
                    deductions.append(f"Skipped heading level (h{levels[i-1]} → h{levels[i]}) (-3)")
                    break
        else:
            score -= 10
            deductions.append("No headings found (-10)")

        # 5. Color contrast (basic check — look for very light text on light bg)
        # This is a heuristic; real contrast requires rendering
        if 'color:#fff' in html.lower() and 'background:#fff' in html.lower():
            score -= 10
            deductions.append("Potential contrast issue: white on white (-10)")

        # 6. Focus indicators
        if "focus:" in html or "focus-visible" in html:
            details.append("Focus indicators present")
        else:
            score -= 5
            deductions.append("No focus indicators found (-5)")

        return DimensionScore(
            dimension=self.dimension,
            score=max(0, score),
            details=details,
            deductions=deductions,
        )


# ══════════════════════════════════════════════════════════════════════════════
# SEO SCORER
# ══════════════════════════════════════════════════════════════════════════════

class SEOScorer(BaseDimensionScorer):
    dimension = EvalDimension.SEO

    def score(self, html: str, **kwargs) -> DimensionScore:
        score = 100.0
        details = []
        deductions = []

        # 1. H1 tag
        h1_count = len(re.findall(r"<h1\b", html, re.I))
        if h1_count == 1:
            details.append("Single h1 tag ✓")
        elif h1_count == 0:
            score -= 15
            deductions.append("No h1 tag found (-15)")
        else:
            score -= 10
            deductions.append(f"Multiple h1 tags ({h1_count}) (-10)")

        # 2. Meta description (in full HTML)
        if '<meta name="description"' in html.lower() or "meta_description" in kwargs.get("spec_json", ""):
            details.append("Meta description present ✓")
        else:
            score -= 10
            deductions.append("No meta description (-10)")

        # 3. Title tag
        if "<title>" in html.lower():
            details.append("Title tag present ✓")
        else:
            score -= 10
            deductions.append("No title tag (-10)")

        # 4. Link quality
        empty_links = len(re.findall(r'<a[^>]*>\s*</a>', html, re.I))
        if empty_links:
            penalty = min(empty_links * 3, 15)
            score -= penalty
            deductions.append(f"{empty_links} empty links (-{penalty})")

        # 5. Image alt text (SEO perspective)
        imgs = re.findall(r"<img\b[^>]*>", html, re.I)
        meaningful_alts = sum(1 for img in imgs if re.search(r'alt="[^"]{3,}"', img, re.I))
        if imgs and meaningful_alts == len(imgs):
            details.append("All images have meaningful alt text ✓")
        elif imgs:
            score -= 5
            deductions.append(f"Some images missing meaningful alt text (-5)")

        # 6. Heading structure
        h_tags = re.findall(r"<h[2-6]\b", html, re.I)
        if len(h_tags) >= 2:
            details.append(f"Good heading structure ({len(h_tags)} sub-headings)")
        elif h1_count > 0:
            score -= 5
            deductions.append("Limited heading structure (-5)")

        return DimensionScore(
            dimension=self.dimension,
            score=max(0, score),
            details=details,
            deductions=deductions,
        )


# ══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE SCORER
# ══════════════════════════════════════════════════════════════════════════════

class PerformanceScorer(BaseDimensionScorer):
    dimension = EvalDimension.PERFORMANCE

    def score(self, html: str, **kwargs) -> DimensionScore:
        score = 100.0
        details = []
        deductions = []

        # 1. HTML size
        size_kb = len(html.encode("utf-8")) / 1024
        if size_kb < 50:
            details.append(f"Compact HTML ({size_kb:.1f} KB)")
        elif size_kb < 150:
            details.append(f"Reasonable HTML size ({size_kb:.1f} KB)")
        elif size_kb < 500:
            score -= 10
            deductions.append(f"Large HTML ({size_kb:.1f} KB) (-10)")
        else:
            score -= 20
            deductions.append(f"Oversized HTML ({size_kb:.1f} KB) (-20)")

        # 2. Inline style count
        inline_count = len(re.findall(r'style="', html, re.I))
        if inline_count <= 20:
            details.append(f"Low inline styles ({inline_count})")
        elif inline_count <= 50:
            score -= 5
            deductions.append(f"Moderate inline styles ({inline_count}) (-5)")
        else:
            score -= 10
            deductions.append(f"Excessive inline styles ({inline_count}) (-10)")

        # 3. Script tag check (should be zero)
        scripts = len(re.findall(r"<script\b", html, re.I))
        if scripts == 0:
            details.append("No script tags ✓")
        else:
            score -= 15
            deductions.append(f"Contains {scripts} script tag(s) (-15)")

        # 4. Image optimization hints
        imgs = re.findall(r"<img\b[^>]*>", html, re.I)
        lazy_loaded = sum(1 for img in imgs if 'loading="lazy"' in img.lower())
        if imgs and lazy_loaded > 0:
            details.append(f"{lazy_loaded}/{len(imgs)} images use lazy loading")
        elif len(imgs) > 3:
            score -= 5
            deductions.append("No lazy loading on images (-5)")

        # 5. CSS efficiency
        # Check for Tailwind utility usage (efficient)
        tailwind_classes = len(re.findall(r'class="[^"]*"', html))
        if tailwind_classes > 10:
            details.append(f"Good Tailwind utility usage ({tailwind_classes} class attrs)")

        return DimensionScore(
            dimension=self.dimension,
            score=max(0, score),
            details=details,
            deductions=deductions,
        )


# ══════════════════════════════════════════════════════════════════════════════
# RESPONSIVENESS SCORER
# ══════════════════════════════════════════════════════════════════════════════

class ResponsivenessScorer(BaseDimensionScorer):
    dimension = EvalDimension.RESPONSIVENESS

    def score(self, html: str, **kwargs) -> DimensionScore:
        score = 100.0
        details = []
        deductions = []

        # 1. Viewport meta
        if 'viewport' in html.lower():
            details.append("Viewport meta tag present ✓")
        else:
            score -= 15
            deductions.append("No viewport meta tag (-15)")

        # 2. Responsive Tailwind classes
        responsive_prefixes = ["sm:", "md:", "lg:", "xl:", "2xl:"]
        found_prefixes = [p for p in responsive_prefixes if p in html]
        if len(found_prefixes) >= 3:
            details.append(f"Good responsive breakpoints: {', '.join(found_prefixes)}")
        elif len(found_prefixes) >= 1:
            score -= 10
            deductions.append(f"Limited responsive classes ({len(found_prefixes)}/3+) (-10)")
        else:
            score -= 25
            deductions.append("No responsive Tailwind classes found (-25)")

        # 3. Mobile-first patterns
        has_flex = "flex" in html
        has_grid = "grid" in html
        if has_flex and has_grid:
            details.append("Uses both Flexbox and Grid layouts ✓")
        elif has_flex or has_grid:
            details.append(f"Uses {'Flexbox' if has_flex else 'Grid'} layout")
        else:
            score -= 10
            deductions.append("No Flexbox or Grid usage (-10)")

        # 4. Max-width containers
        if "max-w-" in html:
            details.append("Max-width containers present ✓")
        else:
            score -= 10
            deductions.append("No max-width containers (-10)")

        # 5. Responsive text
        text_responsive = any(f"{p}text-" in html for p in responsive_prefixes)
        if text_responsive:
            details.append("Responsive text sizing ✓")
        else:
            score -= 5
            deductions.append("No responsive text sizing (-5)")

        # 6. Responsive spacing
        spacing_responsive = any(
            f"{p}p" in html or f"{p}m" in html or f"{p}gap" in html
            for p in responsive_prefixes
        )
        if spacing_responsive:
            details.append("Responsive spacing ✓")

        return DimensionScore(
            dimension=self.dimension,
            score=max(0, score),
            details=details,
            deductions=deductions,
        )


# ══════════════════════════════════════════════════════════════════════════════
# VISUAL CONSISTENCY SCORER
# ══════════════════════════════════════════════════════════════════════════════

class VisualConsistencyScorer(BaseDimensionScorer):
    dimension = EvalDimension.VISUAL_CONSISTENCY

    def score(self, html: str, **kwargs) -> DimensionScore:
        score = 100.0
        details = []
        deductions = []

        # 1. CSS custom properties (theme consistency)
        has_css_vars = "var(--" in html or ":root" in html
        if has_css_vars:
            details.append("CSS custom properties used ✓")
        else:
            score -= 10
            deductions.append("No CSS custom properties (-10)")

        # 2. Consistent color usage
        inline_colors = re.findall(r'(?:color|background):\s*([#\w]+)', html, re.I)
        unique_colors = set(c.lower() for c in inline_colors if c.startswith("#"))
        if len(unique_colors) <= 8:
            details.append(f"Consistent color palette ({len(unique_colors)} unique colors)")
        elif len(unique_colors) <= 15:
            score -= 5
            deductions.append(f"Many unique colors ({len(unique_colors)}) — may lack consistency (-5)")
        else:
            score -= 15
            deductions.append(f"Too many unique colors ({len(unique_colors)}) (-15)")

        # 3. Font consistency
        font_families = re.findall(r"font-family:\s*([^;'\"]+)", html, re.I)
        unique_fonts = set(f.strip().split(",")[0].strip("' \"") for f in font_families)
        if len(unique_fonts) <= 3:
            details.append(f"Consistent typography ({len(unique_fonts)} font families)")
        else:
            score -= 10
            deductions.append(f"Too many font families ({len(unique_fonts)}) (-10)")

        # 4. Border-radius consistency
        radii = re.findall(r"rounded-(\w+)", html)
        unique_radii = set(radii)
        if len(unique_radii) <= 4:
            details.append("Consistent border-radius usage")
        else:
            score -= 5
            deductions.append(f"Inconsistent border-radius ({len(unique_radii)} variants) (-5)")

        # 5. Spacing system
        spacing_classes = re.findall(r"(?:p|m|gap)-(\d+)", html)
        if spacing_classes:
            unique_spacings = set(spacing_classes)
            if len(unique_spacings) <= 8:
                details.append("Consistent spacing system")
            else:
                score -= 5
                deductions.append(f"Inconsistent spacing ({len(unique_spacings)} values) (-5)")

        # 6. Glass morphism consistency (if used)
        has_backdrop = "backdrop-blur" in html or "backdrop-filter" in html
        has_glass_bg = "bg-white/5" in html or "rgba(255" in html
        if has_backdrop and has_glass_bg:
            details.append("Consistent glassmorphism effects ✓")

        return DimensionScore(
            dimension=self.dimension,
            score=max(0, score),
            details=details,
            deductions=deductions,
        )


# ══════════════════════════════════════════════════════════════════════════════
# PROMPT FIDELITY SCORER
# ══════════════════════════════════════════════════════════════════════════════

class PromptFidelityScorer(BaseDimensionScorer):
    dimension = EvalDimension.PROMPT_FIDELITY

    def score(self, html: str, **kwargs) -> DimensionScore:
        score = 100.0
        details = []
        deductions = []

        analysis = kwargs.get("analysis")
        spec = kwargs.get("spec")

        if not analysis or not spec:
            return DimensionScore(
                dimension=self.dimension,
                score=50.0,
                details=["Cannot evaluate without analysis/spec"],
            )

        # 1. Requested components present
        requested = set(analysis.requested_components)
        generated_types = set()
        if spec and hasattr(spec, 'all_components'):
            generated_types = {c.type.value for c in spec.all_components}

        missing = requested - generated_types
        if not missing:
            details.append(f"All {len(requested)} requested components present ✓")
        else:
            penalty = min(len(missing) * 10, 30)
            score -= penalty
            deductions.append(f"Missing requested components: {missing} (-{penalty})")

        # 2. Website type match
        if spec and analysis:
            if spec.website_type == analysis.website_type:
                details.append(f"Website type matches: {analysis.website_type.value} ✓")
            else:
                score -= 10
                deductions.append(f"Type mismatch: asked {analysis.website_type.value}, got {spec.website_type.value} (-10)")

        # 3. Brand name presence
        if analysis.brand_name:
            if analysis.brand_name.lower() in html.lower():
                details.append(f"Brand name '{analysis.brand_name}' found in output ✓")
            else:
                score -= 10
                deductions.append(f"Brand name '{analysis.brand_name}' not found in output (-10)")

        # 4. Theme mode match
        if analysis.theme.value == "dark":
            dark_indicators = ["bg-slate-9", "bg-gray-9", "#020617", "#0f172a", "background:#0"]
            if any(ind in html for ind in dark_indicators):
                details.append("Dark theme correctly applied ✓")
            else:
                score -= 10
                deductions.append("Dark theme not applied (-10)")

        # 5. Industry context
        if analysis.industry != "general":
            details.append(f"Industry context: {analysis.industry}")

        return DimensionScore(
            dimension=self.dimension,
            score=max(0, score),
            details=details,
            deductions=deductions,
        )


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT QUALITY SCORER
# ══════════════════════════════════════════════════════════════════════════════

class ComponentQualityScorer(BaseDimensionScorer):
    dimension = EvalDimension.COMPONENT_QUALITY

    def score(self, html: str, **kwargs) -> DimensionScore:
        score = 100.0
        details = []
        deductions = []

        spec = kwargs.get("spec")
        component_scores: dict[str, float] = {}

        if not spec or not hasattr(spec, 'all_components'):
            return DimensionScore(dimension=self.dimension, score=50.0, details=["No spec"])

        total_components = len(spec.all_components)
        if total_components == 0:
            return DimensionScore(dimension=self.dimension, score=0.0, deductions=["No components"])

        # Score each component by checking its presence in HTML
        for comp in spec.all_components:
            comp_name = comp.type.value
            comp_score = 100.0

            # Check if component's HTML comment marker exists
            if f"<!-- {comp_name} -->" in html:
                comp_score = 90.0  # Base: present with marker
            elif comp_name.lower() in html.lower():
                comp_score = 70.0  # Present but no marker
            else:
                comp_score = 30.0  # Might be missing

            # Check for meaningful content (not just an empty div)
            if comp.props.get("title") and comp.props["title"].lower() in html.lower():
                comp_score += 10
            comp_score = min(100, comp_score)

            component_scores[comp_name] = comp_score

        # Average component scores
        avg = sum(component_scores.values()) / len(component_scores)
        score = avg

        good_count = sum(1 for s in component_scores.values() if s >= 70)
        details.append(f"{good_count}/{total_components} components scored 70+")

        if avg < 60:
            deductions.append(f"Low average component quality ({avg:.0f})")

        dim_score = DimensionScore(
            dimension=self.dimension,
            score=max(0, score),
            details=details,
            deductions=deductions,
        )
        return dim_score


# ══════════════════════════════════════════════════════════════════════════════
# WEBSITE EVALUATOR (ORCHESTRATOR)
# ══════════════════════════════════════════════════════════════════════════════

class WebsiteEvaluator:
    """
    Sprint 1: The Evaluation Engine.

    Scores every generated website across 8 dimensions.
    Now every generation is MEASURABLE.

    Usage:
        evaluator = WebsiteEvaluator()
        result = evaluator.evaluate(pipeline_result)
        # result.overall_score = 92
        # result.grade = "A"
    """

    def __init__(self) -> None:
        self._scorers: list[BaseDimensionScorer] = [
            HTMLQualityScorer(),
            AccessibilityScorer(),
            SEOScorer(),
            PerformanceScorer(),
            ResponsivenessScorer(),
            VisualConsistencyScorer(),
            PromptFidelityScorer(),
            ComponentQualityScorer(),
        ]

    def evaluate(self, pipeline_result: "PipelineResult") -> EvaluationResult:
        """Run all scorers and produce a complete evaluation."""
        start = time.perf_counter()

        html = pipeline_result.html
        result = EvaluationResult(
            prompt=pipeline_result.analysis.requested_components.__repr__() if pipeline_result.analysis else "",
            model="",
            pipeline_version=pipeline_result.pipeline_version,
        )

        kwargs = {
            "analysis": pipeline_result.analysis,
            "spec": pipeline_result.spec,
            "spec_json": pipeline_result.spec.model_dump_json() if pipeline_result.spec else "",
        }

        for scorer in self._scorers:
            try:
                dim_score = scorer.score(html, **kwargs)
                result.dimensions[scorer.dimension] = dim_score
            except Exception as exc:
                logger.error(f"Scorer {scorer.dimension.value} failed: {exc}", exc_info=True)
                result.dimensions[scorer.dimension] = DimensionScore(
                    dimension=scorer.dimension,
                    score=50.0,
                    deductions=[f"Scorer crashed: {exc}"],
                )

        # Extract component scores from component quality scorer
        comp_scorer_result = result.dimensions.get(EvalDimension.COMPONENT_QUALITY)
        if comp_scorer_result:
            # Re-run component scorer to get per-component scores
            comp_scorer = ComponentQualityScorer()
            temp = comp_scorer.score(html, **kwargs)
            # Component scores are embedded in the scorer logic

        result.calculate_overall()
        result.elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(f"Evaluation: {result.summary()}")
        return result

    def evaluate_html(
        self,
        html: str,
        analysis: Optional["PromptAnalysisResult"] = None,
        spec: Optional["WebsiteSpec"] = None,
    ) -> EvaluationResult:
        """Evaluate raw HTML without a full PipelineResult."""
        start = time.perf_counter()

        result = EvaluationResult()
        kwargs = {
            "analysis": analysis,
            "spec": spec,
            "spec_json": spec.model_dump_json() if spec else "",
        }

        for scorer in self._scorers:
            try:
                dim_score = scorer.score(html, **kwargs)
                result.dimensions[scorer.dimension] = dim_score
            except Exception as exc:
                result.dimensions[scorer.dimension] = DimensionScore(
                    dimension=scorer.dimension, score=50.0,
                    deductions=[f"Scorer crashed: {exc}"],
                )

        result.calculate_overall()
        result.elapsed_ms = (time.perf_counter() - start) * 1000
        return result
