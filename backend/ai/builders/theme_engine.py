"""
ai/builders/theme_engine.py — Module 4: ThemeEngine

Resolves color palettes, typography, and design tokens from WebsiteSpec.
Theme is INDEPENDENT of Tailwind classes — it produces abstract tokens
that get mapped to CSS at render time.

Architecture:
  ThemeSpec (from WebsiteSpec)
    ↓
  ThemeEngine
    ↓
  ResolvedTheme (design tokens + Tailwind class map)

Usage:
    engine = ThemeEngine()
    resolved = engine.resolve(spec.theme, analysis)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from schemas.generation import (
    ColorPalette,
    PromptAnalysisResult,
    ThemeMode,
    ThemeSpec,
    ToneStyle,
)


# ── Color Palettes by Hint ───────────────────────────────────────────────────
# When the user says "blue", "neon", etc., we resolve to a curated palette.

COLOR_PALETTES: dict[str, ColorPalette] = {
    "blue": ColorPalette(
        primary="#3b82f6",   secondary="#6366f1",  accent="#06b6d4",
        background="#020617", surface="#0f172a",
        text_primary="#f1f5f9", text_secondary="#94a3b8", border="rgba(59,130,246,0.15)",
    ),
    "green": ColorPalette(
        primary="#10b981",   secondary="#06b6d4",  accent="#34d399",
        background="#022c22", surface="#064e3b",
        text_primary="#ecfdf5", text_secondary="#a7f3d0", border="rgba(16,185,129,0.15)",
    ),
    "purple": ColorPalette(
        primary="#8b5cf6",   secondary="#a78bfa",  accent="#c084fc",
        background="#0c0a1d", surface="#1e1b4b",
        text_primary="#f5f3ff", text_secondary="#c4b5fd", border="rgba(139,92,246,0.15)",
    ),
    "red": ColorPalette(
        primary="#ef4444",   secondary="#f97316",  accent="#fbbf24",
        background="#1a0a0a", surface="#2d1515",
        text_primary="#fef2f2", text_secondary="#fca5a5", border="rgba(239,68,68,0.15)",
    ),
    "orange": ColorPalette(
        primary="#f97316",   secondary="#fb923c",  accent="#fbbf24",
        background="#1a0f05", surface="#2d1a0a",
        text_primary="#fff7ed", text_secondary="#fdba74", border="rgba(249,115,22,0.15)",
    ),
    "pink": ColorPalette(
        primary="#ec4899",   secondary="#f472b6",  accent="#fb7185",
        background="#1a0512", surface="#2d0a1e",
        text_primary="#fdf2f8", text_secondary="#f9a8d4", border="rgba(236,72,153,0.15)",
    ),
    "cyan": ColorPalette(
        primary="#06b6d4",   secondary="#22d3ee",  accent="#67e8f9",
        background="#042f2e", surface="#0e4f4e",
        text_primary="#ecfeff", text_secondary="#a5f3fc", border="rgba(6,182,212,0.15)",
    ),
    "yellow": ColorPalette(
        primary="#eab308",   secondary="#facc15",  accent="#fde047",
        background="#1a1505", surface="#2d220a",
        text_primary="#fefce8", text_secondary="#fde68a", border="rgba(234,179,8,0.15)",
    ),
    "neon": ColorPalette(
        primary="#00ff88",   secondary="#00e5ff",  accent="#ff00ff",
        background="#0a0a0a", surface="#141414",
        text_primary="#ffffff", text_secondary="#b0b0b0", border="rgba(0,255,136,0.15)",
    ),
    "gradient": ColorPalette(
        primary="#6366f1",   secondary="#ec4899",  accent="#8b5cf6",
        background="#020617", surface="#0f172a",
        text_primary="#f1f5f9", text_secondary="#94a3b8", border="rgba(99,102,241,0.15)",
    ),
    "pastel": ColorPalette(
        primary="#a78bfa",   secondary="#f9a8d4",  accent="#86efac",
        background="#fefce8", surface="#ffffff",
        text_primary="#1e1b4b", text_secondary="#4c1d95", border="rgba(167,139,250,0.15)",
    ),
}

# Default palette (dark cyan theme)
DEFAULT_DARK_PALETTE = ColorPalette()  # Uses ColorPalette defaults

DEFAULT_LIGHT_PALETTE = ColorPalette(
    primary="#0ea5e9",   secondary="#6366f1",  accent="#f59e0b",
    background="#ffffff", surface="#f8fafc",
    text_primary="#0f172a", text_secondary="#475569", border="rgba(0,0,0,0.08)",
)

# ── Tone → Additional Style Hints ────────────────────────────────────────────

TONE_STYLE_MAP: dict[ToneStyle, dict] = {
    ToneStyle.MODERN: {
        "border_radius": "0.75rem",
        "glass_effect": True,
        "heading_font": "Inter",
        "body_font": "Inter",
    },
    ToneStyle.MINIMAL: {
        "border_radius": "0.25rem",
        "glass_effect": False,
        "heading_font": "Inter",
        "body_font": "Inter",
    },
    ToneStyle.BOLD: {
        "border_radius": "1rem",
        "glass_effect": True,
        "heading_font": "Outfit",
        "body_font": "Inter",
    },
    ToneStyle.PLAYFUL: {
        "border_radius": "1.5rem",
        "glass_effect": True,
        "heading_font": "Outfit",
        "body_font": "Inter",
    },
    ToneStyle.CORPORATE: {
        "border_radius": "0.5rem",
        "glass_effect": False,
        "heading_font": "Inter",
        "body_font": "Inter",
    },
    ToneStyle.ELEGANT: {
        "border_radius": "0.25rem",
        "glass_effect": True,
        "heading_font": "Playfair Display",
        "body_font": "Inter",
    },
    ToneStyle.TECHY: {
        "border_radius": "0.5rem",
        "glass_effect": True,
        "heading_font": "JetBrains Mono",
        "body_font": "Inter",
    },
    ToneStyle.CREATIVE: {
        "border_radius": "1rem",
        "glass_effect": True,
        "heading_font": "Outfit",
        "body_font": "Inter",
    },
}


# ── Resolved Theme ───────────────────────────────────────────────────────────

@dataclass
class ResolvedTheme:
    """
    Fully resolved theme with design tokens ready for CSS generation.

    This is the output of the ThemeEngine.
    Components use this for consistent styling.
    """
    colors: ColorPalette
    mode: ThemeMode
    tone: ToneStyle
    heading_font: str = "Inter"
    body_font: str = "Inter"
    border_radius: str = "0.75rem"
    glass_effect: bool = True

    # ── Tailwind Class Helpers ───────────────────────────────────────────

    @property
    def bg_class(self) -> str:
        """Background color as inline style (since we use custom colors)."""
        return f"background:{self.colors.background}"

    @property
    def surface_class(self) -> str:
        return f"background:{self.colors.surface}"

    @property
    def text_class(self) -> str:
        return f"color:{self.colors.text_primary}"

    @property
    def text_muted_class(self) -> str:
        return f"color:{self.colors.text_secondary}"

    @property
    def accent_class(self) -> str:
        return f"color:{self.colors.primary}"

    @property
    def css_variables(self) -> str:
        """Generate CSS custom properties for the theme."""
        return f""":root {{
  --color-primary: {self.colors.primary};
  --color-secondary: {self.colors.secondary};
  --color-accent: {self.colors.accent};
  --color-bg: {self.colors.background};
  --color-surface: {self.colors.surface};
  --color-text: {self.colors.text_primary};
  --color-text-muted: {self.colors.text_secondary};
  --color-border: {self.colors.border};
  --radius: {self.border_radius};
  --font-heading: '{self.heading_font}', system-ui, sans-serif;
  --font-body: '{self.body_font}', system-ui, sans-serif;
}}"""

    @property
    def font_imports(self) -> str:
        """Generate Google Fonts import links."""
        fonts = set()
        for font in [self.heading_font, self.body_font]:
            if font not in ("system-ui", "sans-serif", "monospace"):
                fonts.add(font.replace(" ", "+"))
        if not fonts:
            return ""
        families = "&".join(f"family={f}:wght@300;400;500;600;700;800;900" for f in fonts)
        return f'<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?{families}&display=swap" rel="stylesheet">'


# ── ThemeEngine ──────────────────────────────────────────────────────────────

class ThemeEngine:
    """
    Module 4: Resolves theme preferences into concrete design tokens.

    Input: ThemeSpec (from WebsiteSpec) + PromptAnalysisResult
    Output: ResolvedTheme (CSS variables, font imports, color palette)
    """

    def resolve(
        self,
        theme_spec: ThemeSpec,
        analysis: PromptAnalysisResult,
    ) -> ResolvedTheme:
        """Resolve abstract theme preferences into concrete design tokens."""

        # Step 1: Resolve color palette
        colors = self._resolve_colors(theme_spec, analysis)

        # Step 2: Resolve tone-based style hints
        tone_hints = TONE_STYLE_MAP.get(theme_spec.tone, TONE_STYLE_MAP[ToneStyle.MODERN])

        # Step 3: Build resolved theme
        return ResolvedTheme(
            colors=colors,
            mode=theme_spec.mode,
            tone=theme_spec.tone,
            heading_font=tone_hints["heading_font"],
            body_font=tone_hints["body_font"],
            border_radius=tone_hints["border_radius"],
            glass_effect=tone_hints["glass_effect"],
        )

    def _resolve_colors(
        self,
        theme_spec: ThemeSpec,
        analysis: PromptAnalysisResult,
    ) -> ColorPalette:
        """
        Resolve the color palette.

        Priority:
        1. User-specified color hint (e.g., "blue", "neon")
        2. Theme spec explicit colors (if non-default)
        3. Theme mode default (dark/light)
        """
        # Check for color hint from the analysis
        if analysis.color_hint and analysis.color_hint in COLOR_PALETTES:
            palette = COLOR_PALETTES[analysis.color_hint]
            # If light mode but using a dark palette, adjust backgrounds
            if theme_spec.mode == ThemeMode.LIGHT:
                palette = ColorPalette(
                    primary=palette.primary,
                    secondary=palette.secondary,
                    accent=palette.accent,
                    background="#ffffff",
                    surface="#f8fafc",
                    text_primary="#0f172a",
                    text_secondary="#475569",
                    border=palette.border,
                )
            return palette

        # Check for pastel hint (always light mode)
        if analysis.color_hint == "pastel":
            return COLOR_PALETTES["pastel"]

        # Default based on mode
        if theme_spec.mode == ThemeMode.LIGHT:
            return DEFAULT_LIGHT_PALETTE

        return DEFAULT_DARK_PALETTE
