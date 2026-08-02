"""
ai/repair/engine.py — Module 9: RepairEngine

The repair engine takes a ValidationReport and attempts to fix issues.

Two repair strategies:
  1. RegexRepairStrategy: deterministic fixes (strip code fences, close tags, etc.)
  2. AIRepairStrategy: re-prompt the LLM with error context (future)

Architecture:
  HTML + ValidationReport
    ↓
  RepairEngine
    ↓
  RegexRepairStrategy (fast, deterministic)
    ↓
  Validate again
    ↓
  Pass? → Done
  Fail? → Retry (max_retries)

The repair loop:
  1. Validate → report
  2. If valid → return
  3. If errors → repair
  4. Validate again → report
  5. Repeat until valid or max retries reached
"""
from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod

from ai.validators.chain import ValidationIssue, ValidationReport, ValidatorChain

logger = logging.getLogger("ai-site-gen")


# ── Repair Strategy Interface ────────────────────────────────────────────────

class BaseRepairStrategy(ABC):
    """Abstract base for repair strategies."""
    name: str = "BaseRepair"

    @abstractmethod
    def repair(self, html: str, issues: list[ValidationIssue]) -> str:
        """Attempt to repair HTML based on validation issues."""
        ...


# ── Regex Repair Strategy ────────────────────────────────────────────────────

class RegexRepairStrategy(BaseRepairStrategy):
    """
    Deterministic, regex-based repairs.
    Fast and reliable — no LLM needed.
    """
    name = "RegexRepair"

    def repair(self, html: str, issues: list[ValidationIssue]) -> str:
        """Apply regex-based fixes for known issue patterns."""
        repaired = html

        for issue in issues:
            hint = issue.fix_hint
            if not hint:
                continue

            if hint == "strip_code_fences":
                repaired = self._strip_code_fences(repaired)
            elif hint == "strip_think_blocks":
                repaired = self._strip_think_blocks(repaired)
            elif hint == "strip_dangerous_content":
                repaired = self._strip_dangerous_content(repaired)
            elif hint == "trim_leading_text":
                repaired = self._trim_leading_text(repaired)
            elif hint == "close_unclosed_tags":
                repaired = self._close_unclosed_tags(repaired)
            elif hint == "add_alt_attribute":
                repaired = self._add_alt_attributes(repaired)
            elif hint == "add_aria_labels":
                repaired = self._add_aria_labels(repaired)

        return repaired

    def _strip_code_fences(self, html: str) -> str:
        """Remove markdown code fences."""
        html = re.sub(r"```(?:html|HTML)?\s*\n?", "", html)
        html = re.sub(r"```\s*$", "", html)
        return html.strip()

    def _strip_think_blocks(self, html: str) -> str:
        """Remove LLM <think> blocks."""
        html = re.sub(r"<think>.*?</think>", "", html, flags=re.I | re.DOTALL)
        html = re.sub(r"<think>.*$", "", html, flags=re.I | re.DOTALL)
        return html.strip()

    def _strip_dangerous_content(self, html: str) -> str:
        """Remove script tags, event handlers, and dangerous URLs."""
        # Remove script tags entirely
        html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.I | re.DOTALL)
        html = re.sub(r"<script\b[^>]*/>", "", html, flags=re.I)
        # Remove iframe, object, embed
        html = re.sub(r"<iframe\b[^>]*>.*?</iframe>", "", html, flags=re.I | re.DOTALL)
        html = re.sub(r"<object\b[^>]*>.*?</object>", "", html, flags=re.I | re.DOTALL)
        html = re.sub(r"<embed\b[^>]*>", "", html, flags=re.I)
        # Remove inline event handlers (onclick, onmouseover, etc.)
        html = re.sub(r'\s+on\w+\s*=\s*"[^"]*"', "", html, flags=re.I)
        html = re.sub(r"\s+on\w+\s*=\s*'[^']*'", "", html, flags=re.I)
        # Remove javascript: URLs
        html = re.sub(r'href\s*=\s*"javascript:[^"]*"', 'href="#"', html, flags=re.I)
        html = re.sub(r"href\s*=\s*'javascript:[^']*'", "href='#'", html, flags=re.I)
        return html

    def _trim_leading_text(self, html: str) -> str:
        """Trim non-HTML text before the first tag."""
        idx = html.find("<")
        if idx > 0:
            return html[idx:]
        return html

    def _close_unclosed_tags(self, html: str) -> str:
        """
        Simple heuristic: count open/close for major block tags
        and append closing tags if needed.
        """
        block_tags = ["section", "div", "nav", "main", "footer", "header", "article"]
        for tag in block_tags:
            opens = len(re.findall(rf"<{tag}\b", html, re.I))
            closes = len(re.findall(rf"</{tag}>", html, re.I))
            diff = opens - closes
            if diff > 0:
                html += f"\n</{tag}>" * diff
        return html

    def _add_alt_attributes(self, html: str) -> str:
        """Add empty alt attributes to images missing them."""
        def add_alt(match):
            tag = match.group(0)
            if "alt=" not in tag.lower():
                return tag[:-1] + ' alt="">'
            return tag
        return re.sub(r"<img\b[^>]*>", add_alt, html, flags=re.I)

    def _add_aria_labels(self, html: str) -> str:
        """Add aria-label to inputs missing labels."""
        def add_label(match):
            tag = match.group(0)
            if "aria-label" not in tag.lower():
                # Try to use placeholder as label
                placeholder = re.search(r'placeholder="([^"]*)"', tag, re.I)
                label = placeholder.group(1) if placeholder else "Input field"
                return tag[:-1] + f' aria-label="{label}">'
            return tag
        return re.sub(r"<input\b[^>]*>", add_label, html, flags=re.I)


# ── RepairEngine ─────────────────────────────────────────────────────────────

class RepairEngine:
    """
    Module 9: Iterative repair loop.

    validate → repair → validate → repeat

    Usage:
        engine = RepairEngine()
        repaired_html, final_report = engine.repair(html, chain)
    """

    def __init__(
        self,
        strategies: list[BaseRepairStrategy] | None = None,
        max_retries: int = 3,
    ) -> None:
        self._strategies = strategies or [RegexRepairStrategy()]
        self._max_retries = max_retries

    def repair(
        self,
        html: str,
        chain: ValidatorChain,
    ) -> tuple[str, ValidationReport]:
        """
        Iteratively repair HTML until valid or max retries reached.

        Args:
            html: Raw HTML to validate and repair
            chain: ValidatorChain to use for validation

        Returns:
            Tuple of (repaired HTML, final ValidationReport)
        """
        current_html = html

        for attempt in range(self._max_retries + 1):
            # Validate
            report = chain.validate(current_html)

            if report.is_valid:
                if attempt > 0:
                    logger.info(
                        f"Repair succeeded after {attempt} attempt(s) — "
                        f"{report.summary()}"
                    )
                else:
                    logger.info(f"HTML passed validation — {report.summary()}")
                return current_html, report

            if attempt == self._max_retries:
                logger.warning(
                    f"Repair exhausted {self._max_retries} retries — "
                    f"returning best effort. {report.summary()}"
                )
                return current_html, report

            # Apply repairs
            logger.info(
                f"Repair attempt {attempt + 1}/{self._max_retries} — "
                f"{len(report.errors)} errors to fix"
            )
            for strategy in self._strategies:
                try:
                    current_html = strategy.repair(current_html, report.errors)
                except Exception as exc:
                    logger.error(
                        f"Repair strategy {strategy.name} failed: {exc}",
                        exc_info=True,
                    )

        return current_html, chain.validate(current_html)
