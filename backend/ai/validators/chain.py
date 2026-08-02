"""
ai/validators/chain.py — Module 8: ValidatorChain

Runs a pipeline of validators against generated HTML.
Each validator checks one concern (HTML structure, security, SEO, etc.)
and returns a ValidationResult with severity + issues.

Architecture:
  HTML
    ↓
  ValidatorChain
    ↓
  HTMLValidator → SecurityValidator → SEOValidator → AccessibilityValidator
    ↓
  ValidationReport (aggregate)

The chain passes ALL validators — it doesn't stop on first failure.
The RepairEngine (Module 9) then fixes issues based on severity.
"""
from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger("ai-site-gen")


# ── Severity Levels ──────────────────────────────────────────────────────────

class Severity(str, Enum):
    ERROR   = "error"     # Must fix — blocks output
    WARNING = "warning"   # Should fix — degrades quality
    INFO    = "info"      # Optional improvement


# ── Validation Result ────────────────────────────────────────────────────────

@dataclass
class ValidationIssue:
    """A single issue found by a validator."""
    validator: str
    severity: Severity
    message: str
    fix_hint: Optional[str] = None  # Hint for the RepairEngine


@dataclass
class ValidationReport:
    """Aggregate result from all validators in the chain."""
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def is_valid(self) -> bool:
        """True if no errors (warnings are acceptable)."""
        return len(self.errors) == 0

    @property
    def score(self) -> float:
        """Quality score 0-100. Errors subtract 20, warnings subtract 5."""
        score = 100.0
        score -= len(self.errors) * 20
        score -= len(self.warnings) * 5
        return max(0.0, score)

    def summary(self) -> str:
        return (
            f"Score: {self.score:.0f}/100 | "
            f"Errors: {len(self.errors)} | "
            f"Warnings: {len(self.warnings)} | "
            f"Info: {len([i for i in self.issues if i.severity == Severity.INFO])}"
        )


# ── Base Validator ───────────────────────────────────────────────────────────

class BaseValidator(ABC):
    """Abstract base for all HTML validators."""
    name: str = "BaseValidator"

    @abstractmethod
    def validate(self, html: str) -> list[ValidationIssue]:
        """Validate HTML and return a list of issues."""
        ...


# ── Concrete Validators ─────────────────────────────────────────────────────

class HTMLStructureValidator(BaseValidator):
    """Validates basic HTML structure and well-formedness."""
    name = "HTMLStructure"

    def validate(self, html: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        # Check for empty output
        if not html or len(html.strip()) < 20:
            issues.append(ValidationIssue(
                validator=self.name,
                severity=Severity.ERROR,
                message="HTML output is empty or too short",
                fix_hint="regenerate_component",
            ))
            return issues

        # Check for unclosed tags (simple heuristic)
        open_tags = re.findall(r"<(section|div|nav|main|footer|header|article)\b", html, re.I)
        close_tags = re.findall(r"</(section|div|nav|main|footer|header|article)>", html, re.I)
        if len(open_tags) > len(close_tags) + 2:
            issues.append(ValidationIssue(
                validator=self.name,
                severity=Severity.ERROR,
                message=f"Potentially unclosed tags: {len(open_tags)} opened vs {len(close_tags)} closed",
                fix_hint="close_unclosed_tags",
            ))

        # Check for code fences (LLM artifact)
        if "```" in html:
            issues.append(ValidationIssue(
                validator=self.name,
                severity=Severity.ERROR,
                message="HTML contains markdown code fences (```)",
                fix_hint="strip_code_fences",
            ))

        # Check for think blocks
        if "<think>" in html.lower():
            issues.append(ValidationIssue(
                validator=self.name,
                severity=Severity.ERROR,
                message="HTML contains LLM <think> blocks",
                fix_hint="strip_think_blocks",
            ))

        # Check starts with HTML tag
        stripped = html.strip()
        if stripped and not stripped.startswith("<"):
            issues.append(ValidationIssue(
                validator=self.name,
                severity=Severity.WARNING,
                message="HTML does not start with an HTML tag",
                fix_hint="trim_leading_text",
            ))

        return issues


class SecurityValidator(BaseValidator):
    """Checks for security issues in generated HTML."""
    name = "Security"

    DANGEROUS_PATTERNS = [
        (r"<script\b", "Script tag detected — XSS risk"),
        (r"javascript:", "javascript: URL detected"),
        (r"on\w+\s*=", "Inline event handler detected"),
        (r"<iframe\b", "iframe tag detected"),
        (r"<object\b", "object tag detected"),
        (r"<embed\b", "embed tag detected"),
        (r"eval\s*\(", "eval() detected"),
        (r"document\.cookie", "document.cookie access detected"),
        (r"window\.location\s*=", "window.location assignment detected"),
    ]

    def validate(self, html: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        for pattern, message in self.DANGEROUS_PATTERNS:
            if re.search(pattern, html, re.IGNORECASE):
                issues.append(ValidationIssue(
                    validator=self.name,
                    severity=Severity.ERROR,
                    message=message,
                    fix_hint="strip_dangerous_content",
                ))

        return issues


class SEOValidator(BaseValidator):
    """Validates basic SEO best practices."""
    name = "SEO"

    def validate(self, html: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        # Check for heading hierarchy
        h1_count = len(re.findall(r"<h1\b", html, re.I))
        if h1_count == 0:
            issues.append(ValidationIssue(
                validator=self.name,
                severity=Severity.WARNING,
                message="No <h1> tag found — important for SEO",
                fix_hint="add_h1_tag",
            ))
        elif h1_count > 1:
            issues.append(ValidationIssue(
                validator=self.name,
                severity=Severity.WARNING,
                message=f"Multiple <h1> tags found ({h1_count}) — use only one per page",
            ))

        # Check for alt attributes on images
        img_tags = re.findall(r"<img\b[^>]*>", html, re.I)
        for img in img_tags:
            if "alt=" not in img.lower():
                issues.append(ValidationIssue(
                    validator=self.name,
                    severity=Severity.WARNING,
                    message="Image missing alt attribute",
                    fix_hint="add_alt_attribute",
                ))
                break  # Report once

        # Check for empty links
        empty_links = re.findall(r'<a[^>]*>\s*</a>', html, re.I)
        if empty_links:
            issues.append(ValidationIssue(
                validator=self.name,
                severity=Severity.WARNING,
                message=f"Found {len(empty_links)} empty link(s)",
            ))

        return issues


class AccessibilityValidator(BaseValidator):
    """Validates basic WCAG accessibility requirements."""
    name = "Accessibility"

    def validate(self, html: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        # Check for landmark roles
        has_nav = "<nav" in html.lower()
        has_main = "<main" in html.lower() or "<section" in html.lower()
        has_footer = "<footer" in html.lower()

        if not has_nav:
            issues.append(ValidationIssue(
                validator=self.name,
                severity=Severity.INFO,
                message="No <nav> landmark found",
            ))

        # Check for button accessibility
        buttons = re.findall(r"<button\b[^>]*>", html, re.I)
        for btn in buttons:
            if "aria-label" not in btn.lower() and ">" not in btn:
                issues.append(ValidationIssue(
                    validator=self.name,
                    severity=Severity.INFO,
                    message="Button may be missing accessible label",
                ))
                break

        # Check for form labels
        inputs = re.findall(r"<input\b[^>]*>", html, re.I)
        if inputs and "<label" not in html.lower():
            issues.append(ValidationIssue(
                validator=self.name,
                severity=Severity.WARNING,
                message="Form inputs found without <label> elements",
                fix_hint="add_aria_labels",
            ))

        return issues


class PerformanceValidator(BaseValidator):
    """Validates performance best practices."""
    name = "Performance"

    def validate(self, html: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        # Check for inline styles (excessive)
        inline_count = len(re.findall(r'style="', html, re.I))
        if inline_count > 50:
            issues.append(ValidationIssue(
                validator=self.name,
                severity=Severity.INFO,
                message=f"High number of inline styles ({inline_count}) — consider using CSS classes",
            ))

        # Check for very large output
        if len(html) > 100_000:
            issues.append(ValidationIssue(
                validator=self.name,
                severity=Severity.WARNING,
                message=f"HTML output is very large ({len(html):,} chars)",
            ))

        return issues


# ── ValidatorChain ───────────────────────────────────────────────────────────

class ValidatorChain:
    """
    Module 8: Runs all validators and produces a ValidationReport.

    Usage:
        chain = ValidatorChain.default()
        report = chain.validate(html)
        if not report.is_valid:
            # send to RepairEngine
    """

    def __init__(self, validators: list[BaseValidator] | None = None) -> None:
        self._validators = validators or []

    @classmethod
    def default(cls) -> "ValidatorChain":
        """Create chain with all default validators."""
        return cls([
            HTMLStructureValidator(),
            SecurityValidator(),
            SEOValidator(),
            AccessibilityValidator(),
            PerformanceValidator(),
        ])

    def add(self, validator: BaseValidator) -> "ValidatorChain":
        """Add a validator to the chain. Returns self for chaining."""
        self._validators.append(validator)
        return self

    def validate(self, html: str) -> ValidationReport:
        """Run all validators and return aggregate report."""
        report = ValidationReport()

        for validator in self._validators:
            try:
                issues = validator.validate(html)
                report.issues.extend(issues)
                logger.debug(
                    f"Validator {validator.name}: {len(issues)} issues"
                )
            except Exception as exc:
                logger.error(
                    f"Validator {validator.name} crashed: {exc}",
                    exc_info=True,
                )
                report.issues.append(ValidationIssue(
                    validator=validator.name,
                    severity=Severity.WARNING,
                    message=f"Validator crashed: {exc}",
                ))

        logger.info(f"Validation complete — {report.summary()}")
        return report
