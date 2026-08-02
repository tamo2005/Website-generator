"""
evaluation/rubric.py — Scoring Rubric Definitions

Defines the evaluation dimensions and their weights.
Each dimension has sub-criteria with scoring functions.

Architecture:
  Every generated website receives a multi-dimensional score:
    - HTML Quality (structure, semantics, well-formedness)
    - Accessibility (WCAG, landmarks, alt text, labels)
    - SEO (headings, meta, links, structure)
    - Performance (size, inline styles, complexity)
    - Responsiveness (mobile classes, viewport, breakpoints)
    - Visual Consistency (color usage, spacing, typography)
    - Prompt Fidelity (did we build what was asked?)
    - Component Quality (per-component scoring)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EvalDimension(str, Enum):
    """Evaluation dimensions — each gets a 0-100 score."""
    HTML_QUALITY       = "html_quality"
    ACCESSIBILITY      = "accessibility"
    SEO                = "seo"
    PERFORMANCE        = "performance"
    RESPONSIVENESS     = "responsiveness"
    VISUAL_CONSISTENCY = "visual_consistency"
    PROMPT_FIDELITY    = "prompt_fidelity"
    COMPONENT_QUALITY  = "component_quality"


# Weights determine overall score contribution (must sum to 1.0)
DIMENSION_WEIGHTS: dict[EvalDimension, float] = {
    EvalDimension.HTML_QUALITY:       0.10,
    EvalDimension.ACCESSIBILITY:      0.10,
    EvalDimension.SEO:                0.10,
    EvalDimension.PERFORMANCE:        0.10,
    EvalDimension.RESPONSIVENESS:     0.15,
    EvalDimension.VISUAL_CONSISTENCY: 0.15,
    EvalDimension.PROMPT_FIDELITY:    0.20,
    EvalDimension.COMPONENT_QUALITY:  0.10,
}


@dataclass
class DimensionScore:
    """Score for a single evaluation dimension."""
    dimension: EvalDimension
    score: float                           # 0-100
    max_score: float = 100.0
    details: list[str] = field(default_factory=list)    # Human-readable notes
    deductions: list[str] = field(default_factory=list)  # What went wrong
    weight: float = 0.0

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight

    @property
    def percentage(self) -> float:
        return (self.score / self.max_score) * 100 if self.max_score > 0 else 0


@dataclass
class EvaluationResult:
    """
    Complete evaluation result for a generated website.

    This is stored with every generation and used for:
      - Quality tracking over time
      - A/B testing between models
      - Prompt version comparison
      - Component-level benchmarking
    """
    dimensions: dict[EvalDimension, DimensionScore] = field(default_factory=dict)
    overall_score: float = 0.0
    grade: str = ""           # A+, A, B+, B, C, D, F
    component_scores: dict[str, float] = field(default_factory=dict)  # per-component scores
    prompt: str = ""
    model: str = ""
    pipeline_version: str = "V1"
    elapsed_ms: float = 0.0

    def calculate_overall(self) -> None:
        """Calculate weighted overall score from dimension scores."""
        total = 0.0
        for dim, score in self.dimensions.items():
            weight = DIMENSION_WEIGHTS.get(dim, 0.0)
            score.weight = weight
            total += score.score * weight
        self.overall_score = round(total, 1)
        self.grade = self._to_grade(self.overall_score)

    @staticmethod
    def _to_grade(score: float) -> str:
        if score >= 95: return "A+"
        if score >= 90: return "A"
        if score >= 85: return "B+"
        if score >= 80: return "B"
        if score >= 70: return "C"
        if score >= 60: return "D"
        return "F"

    def to_dict(self) -> dict:
        """Serialize for storage."""
        return {
            "overall_score": self.overall_score,
            "grade": self.grade,
            "dimensions": {
                dim.value: {
                    "score": round(ds.score, 1),
                    "weight": ds.weight,
                    "weighted": round(ds.weighted_score, 1),
                    "details": ds.details,
                    "deductions": ds.deductions,
                }
                for dim, ds in self.dimensions.items()
            },
            "component_scores": self.component_scores,
            "prompt": self.prompt[:200],
            "model": self.model,
            "pipeline_version": self.pipeline_version,
            "elapsed_ms": round(self.elapsed_ms, 1),
        }

    def summary(self) -> str:
        """One-line summary for logging."""
        dim_str = " | ".join(
            f"{d.value.split('_')[0]}={s.score:.0f}"
            for d, s in self.dimensions.items()
        )
        return f"Overall: {self.overall_score:.0f} ({self.grade}) | {dim_str}"
