"""
ai/planner/analyzer.py — Module 1: PromptAnalyzer

DETERMINISTIC. No LLM calls.

Takes a raw user prompt string and extracts structured metadata:
  - website_type (landing, portfolio, ecommerce, etc.)
  - industry (AI, restaurant, finance, etc.)
  - theme mode (dark/light)
  - tone (modern, minimal, bold, etc.)
  - requested components (pricing, contact, gallery, etc.)
  - brand name hint
  - color hint

Architecture:
  Each detection function is pure and independent.
  Adding a new detection = adding one function + one mapping entry.
  Zero coupling between detectors.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from schemas.generation import (
    PromptAnalysisResult,
    ThemeMode,
    ToneStyle,
    WebsiteType,
)

if TYPE_CHECKING:
    from schemas.generation import GenerationRequest


# ── Keyword Maps ─────────────────────────────────────────────────────────────

WEBSITE_TYPE_KEYWORDS: dict[WebsiteType, list[str]] = {
    WebsiteType.LANDING: [
        "landing", "landing page", "homepage", "home page",
    ],
    WebsiteType.PORTFOLIO: [
        "portfolio", "developer portfolio", "designer portfolio",
        "personal site", "personal website", "freelance",
    ],
    WebsiteType.BLOG: [
        "blog", "article", "magazine", "newsletter", "journal",
    ],
    WebsiteType.ECOMMERCE: [
        "shop", "store", "e-commerce", "ecommerce", "product",
        "marketplace", "buy", "cart",
    ],
    WebsiteType.DASHBOARD: [
        "dashboard", "admin", "analytics", "panel", "stats",
    ],
    WebsiteType.SAAS: [
        "saas", "software as a service", "subscription", "platform",
        "tool", "app", "application",
    ],
    WebsiteType.RESTAURANT: [
        "restaurant", "food", "cafe", "coffee", "bakery",
        "menu", "dining", "eatery", "bistro",
    ],
    WebsiteType.AGENCY: [
        "agency", "consulting", "consultancy", "studio",
        "creative agency", "marketing agency", "design agency",
    ],
    WebsiteType.STARTUP: [
        "startup", "start-up", "tech startup", "ai startup",
    ],
    WebsiteType.DOCS: [
        "documentation", "docs", "api docs", "reference",
    ],
    WebsiteType.PERSONAL: [
        "personal", "resume", "cv", "about me",
    ],
    WebsiteType.BUSINESS: [
        "business", "company", "corporate", "enterprise",
    ],
}

INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "ai": ["ai", "artificial intelligence", "machine learning", "ml", "deep learning", "neural", "gpt", "llm"],
    "finance": ["finance", "fintech", "banking", "payment", "crypto", "trading", "investment", "wallet"],
    "health": ["health", "healthcare", "medical", "fitness", "wellness", "gym", "hospital", "clinic"],
    "education": ["education", "learning", "course", "school", "university", "academy", "tutor", "edtech"],
    "food": ["food", "restaurant", "cafe", "coffee", "bakery", "recipe", "cooking", "delivery"],
    "travel": ["travel", "tourism", "hotel", "booking", "flight", "adventure", "vacation"],
    "fashion": ["fashion", "clothing", "apparel", "style", "boutique", "wear"],
    "music": ["music", "spotify", "playlist", "audio", "streaming", "podcast"],
    "gaming": ["gaming", "game", "esports", "play", "arcade"],
    "real_estate": ["real estate", "property", "housing", "apartment", "rental"],
    "legal": ["legal", "law", "attorney", "lawyer", "law firm"],
    "photography": ["photography", "photo", "photographer", "studio"],
    "technology": ["technology", "tech", "software", "developer", "code", "programming", "devops"],
    "marketing": ["marketing", "seo", "advertising", "branding", "social media"],
    "nonprofit": ["nonprofit", "charity", "ngo", "donation", "cause", "volunteer"],
}

COMPONENT_KEYWORDS: dict[str, list[str]] = {
    "Pricing":       ["pricing", "plans", "subscription", "cost", "price"],
    "FAQ":           ["faq", "questions", "q&a", "frequently asked"],
    "Contact":       ["contact", "reach out", "get in touch", "email us"],
    "Gallery":       ["gallery", "portfolio", "showcase", "images", "photos"],
    "Testimonials":  ["testimonials", "reviews", "what people say", "clients say"],
    "Blog":          ["blog", "articles", "posts", "news"],
    "Newsletter":    ["newsletter", "subscribe", "mailing list", "updates"],
    "Team":          ["team", "our team", "meet the team", "people", "staff"],
    "Stats":         ["stats", "statistics", "numbers", "metrics", "data"],
    "Services":      ["services", "what we do", "offerings"],
    "About":         ["about", "about us", "our story", "who we are", "mission"],
    "CTA":           ["cta", "call to action", "get started", "sign up", "try now"],
    "Menu":          ["menu", "food menu", "dishes"],
    "Reservation":   ["reservation", "booking", "book a table", "reserve"],
    "Projects":      ["projects", "work", "case studies"],
    "Skills":        ["skills", "technologies", "tech stack", "expertise"],
    "HowItWorks":    ["how it works", "process", "steps", "workflow"],
    "Logos":         ["logos", "partners", "clients", "trusted by", "as seen"],
}

THEME_KEYWORDS: dict[ThemeMode, list[str]] = {
    ThemeMode.DARK:  ["dark", "dark mode", "dark theme", "night", "midnight", "slate", "black"],
    ThemeMode.LIGHT: ["light", "white", "bright", "clean", "light mode", "light theme", "minimal white"],
}

TONE_KEYWORDS: dict[ToneStyle, list[str]] = {
    ToneStyle.MODERN:    ["modern", "contemporary", "sleek", "clean"],
    ToneStyle.MINIMAL:   ["minimal", "minimalist", "simple", "bare"],
    ToneStyle.BOLD:      ["bold", "striking", "vibrant", "colorful", "loud"],
    ToneStyle.PLAYFUL:   ["playful", "fun", "quirky", "animated", "cute"],
    ToneStyle.CORPORATE: ["corporate", "professional", "formal", "business"],
    ToneStyle.ELEGANT:   ["elegant", "luxury", "luxurious", "premium", "sophisticated"],
    ToneStyle.TECHY:     ["techy", "hacker", "developer", "code", "terminal", "neon", "cyber"],
    ToneStyle.CREATIVE:  ["creative", "artistic", "design", "experimental"],
}

COLOR_KEYWORDS: dict[str, list[str]] = {
    "blue":     ["blue", "ocean", "sky", "navy", "azure"],
    "green":    ["green", "emerald", "forest", "eco", "nature"],
    "purple":   ["purple", "violet", "lavender", "grape"],
    "red":      ["red", "crimson", "scarlet", "ruby"],
    "orange":   ["orange", "amber", "tangerine", "warm"],
    "pink":     ["pink", "rose", "magenta", "fuchsia"],
    "cyan":     ["cyan", "teal", "aqua", "turquoise"],
    "yellow":   ["yellow", "gold", "golden", "sunshine"],
    "neon":     ["neon", "glow", "fluorescent", "electric"],
    "gradient": ["gradient", "gradients", "blend", "aurora"],
    "pastel":   ["pastel", "soft", "muted", "dusty"],
}


# ── Analyzer ─────────────────────────────────────────────────────────────────

class PromptAnalyzer:
    """
    Module 1: Deterministic prompt analysis.

    Zero LLM calls. Pure keyword/pattern matching.
    Future: can be extended with spaCy NER or Instructor structured outputs.

    Usage:
        analyzer = PromptAnalyzer()
        result = analyzer.analyze("Build a SaaS landing page for an AI startup with pricing")
    """

    def analyze(
        self,
        prompt: str,
        request: "Optional[GenerationRequest]" = None,
    ) -> PromptAnalysisResult:
        """
        Analyze a raw user prompt and extract structured metadata.

        If a GenerationRequest is provided, explicit user selections
        override the deterministic detection.
        """
        lowered = prompt.lower().strip()
        words = set(lowered.split())

        website_type = self._detect_website_type(lowered)
        industry = self._detect_industry(lowered)
        theme = self._detect_theme(lowered)
        tone = self._detect_tone(lowered)
        components = self._detect_components(lowered)
        brand_name = self._detect_brand_name(prompt)
        color_hint = self._detect_color(lowered)

        complexity = self._assess_complexity(prompt, components)

        # Phase 6: Apply GenerationRequest overrides
        if request:
            if request.website_type is not None:
                website_type = request.website_type
            if request.theme is not None:
                theme = request.theme
            if request.color is not None:
                color_hint = request.color
            if request.brand_name is not None:
                brand_name = request.brand_name
            if request.sections:
                # Merge user-selected sections with detected ones
                for section in request.sections:
                    if section not in components:
                        components.append(section)

        return PromptAnalysisResult(
            website_type=website_type,
            industry=industry,
            theme=theme,
            tone=tone,
            requested_components=components,
            detected_keywords=self._collect_keywords(lowered),
            brand_name=brand_name,
            color_hint=color_hint,
            has_pricing="Pricing" in components,
            has_contact="Contact" in components,
            has_gallery="Gallery" in components,
            has_blog="Blog" in components,
            prompt_complexity=complexity,
        )

    # ── Detectors ────────────────────────────────────────────────────────────

    def _detect_website_type(self, lowered: str) -> WebsiteType:
        """Match website type by keyword presence. First match wins (ordered by specificity)."""
        # Check multi-word phrases first (higher specificity)
        scores: dict[WebsiteType, int] = {}
        for wtype, keywords in WEBSITE_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lowered)
            if score > 0:
                scores[wtype] = score

        if scores:
            return max(scores, key=scores.get)  # type: ignore[arg-type]
        return WebsiteType.LANDING  # Default

    def _detect_industry(self, lowered: str) -> str:
        """Match industry by keyword presence."""
        scores: dict[str, int] = {}
        for industry, keywords in INDUSTRY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lowered)
            if score > 0:
                scores[industry] = score

        if scores:
            return max(scores, key=scores.get)  # type: ignore[arg-type]
        return "general"

    def _detect_theme(self, lowered: str) -> ThemeMode:
        """Detect theme mode preference."""
        for mode, keywords in THEME_KEYWORDS.items():
            if any(kw in lowered for kw in keywords):
                return mode
        return ThemeMode.DARK  # Default to dark

    def _detect_tone(self, lowered: str) -> ToneStyle:
        """Detect visual tone/style."""
        scores: dict[ToneStyle, int] = {}
        for tone, keywords in TONE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lowered)
            if score > 0:
                scores[tone] = score

        if scores:
            return max(scores, key=scores.get)  # type: ignore[arg-type]
        return ToneStyle.MODERN  # Default

    def _detect_components(self, lowered: str) -> list[str]:
        """Detect explicitly requested components from the prompt."""
        found: list[str] = []
        for component, keywords in COMPONENT_KEYWORDS.items():
            if any(kw in lowered for kw in keywords):
                if component not in found:
                    found.append(component)
        return found

    def _detect_brand_name(self, original_prompt: str) -> str | None:
        """
        Attempt to extract a brand name from quoted strings or 'called X' / 'named X'.

        Examples:
            'Create a website for "TechNova"'  →  "TechNova"
            'Build a site called Acme Corp'    →  "Acme Corp"
        """
        # Check for quoted names
        quoted = re.findall(r'["\u201c\u201d]([^""\u201c\u201d]+)["\u201c\u201d]', original_prompt)
        if quoted:
            return quoted[0].strip()

        # Check for "called X" or "named X" patterns
        named = re.search(
            r'(?:called|named|for)\s+([A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*){0,3})',
            original_prompt,
        )
        if named:
            return named.group(1).strip()

        return None

    def _detect_color(self, lowered: str) -> str | None:
        """Detect color preference hints."""
        for color, keywords in COLOR_KEYWORDS.items():
            if any(kw in lowered for kw in keywords):
                return color
        return None

    def _assess_complexity(self, prompt: str, components: list[str]) -> str:
        """Assess prompt complexity: simple / standard / complex."""
        word_count = len(prompt.split())
        component_count = len(components)

        if word_count < 10 and component_count <= 1:
            return "simple"
        if word_count > 40 or component_count > 4:
            return "complex"
        return "standard"

    def _collect_keywords(self, lowered: str) -> list[str]:
        """Collect all detected keywords for debugging/logging."""
        found: list[str] = []
        all_maps = [
            WEBSITE_TYPE_KEYWORDS, INDUSTRY_KEYWORDS,
            COMPONENT_KEYWORDS, THEME_KEYWORDS,
            TONE_KEYWORDS, COLOR_KEYWORDS,
        ]
        for keyword_map in all_maps:
            for _key, keywords in keyword_map.items():
                for kw in keywords:
                    if kw in lowered and kw not in found:
                        found.append(kw)
        return found[:20]  # Cap at 20 to avoid noise
