"""
ai/builders/design_resolver.py — Phase 6: DesignResolver (Module 4.5)

Separates WHAT the website is (WebsiteSpec) from HOW it looks (DesignSpec).

    WebsiteSpec + ResolvedTheme + StylePreset
        ↓
    DesignResolver
        ↓
    DesignSpec { button_style, card_style, spacing, animation, variants, ... }

Each StylePreset maps to a coherent set of design tokens.
This is the single decision that makes consistently beautiful websites possible.

Usage:
    resolver = DesignResolver()
    design = resolver.resolve(spec, theme, style_preset, animation_preset)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from schemas.generation import (
    AnimationPreset,
    ContentTone,
    DesignSpec,
    StylePreset,
    WebsiteSpec,
)

if TYPE_CHECKING:
    from ai.builders.theme_engine import ResolvedTheme

logger = logging.getLogger("ai-site-gen")


# ══════════════════════════════════════════════════════════════════════════════
# STYLE PRESET → DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════════════

STYLE_TOKENS: dict[StylePreset, dict] = {
    StylePreset.MODERN: {
        "button_style": "rounded-xl px-6 py-3 font-semibold transition-all duration-200",
        "card_style": "rounded-2xl border backdrop-blur-sm",
        "border_radius": "0.75rem",
        "elevation": "shadow-lg shadow-black/5",
        "glass_effect": False,
        "gradient_enabled": True,
        "container_max_width": "max-w-7xl",
        "spacing_scale": "8px",
        "icon_pack": "lucide",
        "image_style": "editorial",
    },
    StylePreset.MINIMAL: {
        "button_style": "rounded-lg px-5 py-2.5 font-medium border transition-colors",
        "card_style": "rounded-lg border",
        "border_radius": "0.5rem",
        "elevation": "shadow-sm",
        "glass_effect": False,
        "gradient_enabled": False,
        "container_max_width": "max-w-5xl",
        "spacing_scale": "8px",
        "icon_pack": "lucide",
        "image_style": "minimal",
    },
    StylePreset.GLASSMORPHISM: {
        "button_style": "rounded-2xl px-6 py-3 font-semibold backdrop-blur-md bg-white/10 border border-white/20",
        "card_style": "rounded-3xl backdrop-blur-xl bg-white/5 border border-white/10",
        "border_radius": "1.5rem",
        "elevation": "shadow-2xl shadow-black/20",
        "glass_effect": True,
        "gradient_enabled": True,
        "container_max_width": "max-w-7xl",
        "spacing_scale": "8px",
        "icon_pack": "lucide",
        "image_style": "abstract",
    },
    StylePreset.CORPORATE: {
        "button_style": "rounded-lg px-6 py-3 font-semibold",
        "card_style": "rounded-xl border shadow-sm",
        "border_radius": "0.5rem",
        "elevation": "shadow-md",
        "glass_effect": False,
        "gradient_enabled": False,
        "container_max_width": "max-w-6xl",
        "spacing_scale": "8px",
        "icon_pack": "lucide",
        "image_style": "photo",
    },
    StylePreset.LUXURY: {
        "button_style": "rounded-none px-8 py-4 font-light tracking-[0.2em] uppercase text-sm border",
        "card_style": "rounded-none border",
        "border_radius": "0",
        "elevation": "shadow-none",
        "glass_effect": False,
        "gradient_enabled": False,
        "container_max_width": "max-w-6xl",
        "spacing_scale": "12px",
        "icon_pack": "lucide",
        "image_style": "editorial",
    },
    StylePreset.CYBERPUNK: {
        "button_style": "rounded-none px-6 py-3 font-bold uppercase tracking-wider border-2 skew-x-[-2deg]",
        "card_style": "rounded-none border-2 bg-black/60",
        "border_radius": "0",
        "elevation": "shadow-[0_0_20px_rgba(0,255,136,0.3)]",
        "glass_effect": False,
        "gradient_enabled": True,
        "container_max_width": "max-w-7xl",
        "spacing_scale": "8px",
        "icon_pack": "lucide",
        "image_style": "abstract",
    },
    StylePreset.BRUTALIST: {
        "button_style": "rounded-none px-6 py-3 font-black uppercase border-4 border-current",
        "card_style": "rounded-none border-4 border-current",
        "border_radius": "0",
        "elevation": "shadow-[8px_8px_0px_currentColor]",
        "glass_effect": False,
        "gradient_enabled": False,
        "container_max_width": "max-w-6xl",
        "spacing_scale": "8px",
        "icon_pack": "lucide",
        "image_style": "photo",
    },
    StylePreset.APPLE: {
        "button_style": "rounded-full px-8 py-3 font-medium text-sm",
        "card_style": "rounded-3xl",
        "border_radius": "1.5rem",
        "elevation": "shadow-none",
        "glass_effect": False,
        "gradient_enabled": False,
        "container_max_width": "max-w-5xl",
        "spacing_scale": "16px",
        "icon_pack": "lucide",
        "image_style": "editorial",
    },
    StylePreset.STRIPE: {
        "button_style": "rounded-full px-6 py-3 font-semibold",
        "card_style": "rounded-2xl border shadow-lg",
        "border_radius": "1rem",
        "elevation": "shadow-xl shadow-black/5",
        "glass_effect": False,
        "gradient_enabled": True,
        "container_max_width": "max-w-6xl",
        "spacing_scale": "8px",
        "icon_pack": "lucide",
        "image_style": "illustration",
    },
    StylePreset.LINEAR: {
        "button_style": "rounded-lg px-5 py-2.5 font-medium text-sm",
        "card_style": "rounded-xl border border-white/[0.08]",
        "border_radius": "0.75rem",
        "elevation": "shadow-none",
        "glass_effect": False,
        "gradient_enabled": True,
        "container_max_width": "max-w-6xl",
        "spacing_scale": "8px",
        "icon_pack": "lucide",
        "image_style": "abstract",
    },
    StylePreset.NOTION: {
        "button_style": "rounded-lg px-4 py-2 font-medium text-sm border",
        "card_style": "rounded-lg border",
        "border_radius": "0.5rem",
        "elevation": "shadow-sm",
        "glass_effect": False,
        "gradient_enabled": False,
        "container_max_width": "max-w-4xl",
        "spacing_scale": "4px",
        "icon_pack": "lucide",
        "image_style": "minimal",
    },
    StylePreset.VERCEL: {
        "button_style": "rounded-lg px-4 py-2 font-medium text-sm border border-white/20",
        "card_style": "rounded-xl border border-white/[0.08] bg-black",
        "border_radius": "0.75rem",
        "elevation": "shadow-none",
        "glass_effect": False,
        "gradient_enabled": True,
        "container_max_width": "max-w-5xl",
        "spacing_scale": "8px",
        "icon_pack": "lucide",
        "image_style": "abstract",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# ANIMATION PRESETS → CSS CLASSES
# ══════════════════════════════════════════════════════════════════════════════

ANIMATION_CLASSES: dict[AnimationPreset, dict[str, str]] = {
    AnimationPreset.NONE: {
        "reveal": "",
        "hover": "",
        "transition": "",
        "stagger_delay": "0ms",
    },
    AnimationPreset.MINIMAL: {
        "reveal": "animate-fade-in",
        "hover": "hover:opacity-80",
        "transition": "transition-opacity duration-200",
        "stagger_delay": "50ms",
    },
    AnimationPreset.SMOOTH: {
        "reveal": "animate-fade-in-up",
        "hover": "hover:-translate-y-1 hover:shadow-lg",
        "transition": "transition-all duration-300 ease-out",
        "stagger_delay": "100ms",
    },
    AnimationPreset.FANCY: {
        "reveal": "animate-fade-in-up",
        "hover": "hover:-translate-y-2 hover:shadow-2xl hover:scale-[1.02]",
        "transition": "transition-all duration-500 ease-out",
        "stagger_delay": "150ms",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# DESIGN RESOLVER
# ══════════════════════════════════════════════════════════════════════════════

class DesignResolver:
    """
    Phase 6: Module 4.5 — Resolves DesignSpec from style presets.

    Sits between ThemeEngine and ComponentRegistry:
        ThemeEngine → ResolvedTheme (colors, fonts)
        DesignResolver → DesignSpec (layout, spacing, animation, variants)

    Usage:
        resolver = DesignResolver()
        design = resolver.resolve(spec, theme, StylePreset.LINEAR, AnimationPreset.SMOOTH)
    """

    def resolve(
        self,
        spec: WebsiteSpec,
        theme: "ResolvedTheme",
        style: StylePreset = StylePreset.MODERN,
        animation: AnimationPreset = AnimationPreset.SMOOTH,
        content_tone: ContentTone = ContentTone.PROFESSIONAL,
        section_variants: Optional[dict[str, str]] = None,
    ) -> DesignSpec:
        """Resolve a complete DesignSpec from presets."""
        tokens = STYLE_TOKENS.get(style, STYLE_TOKENS[StylePreset.MODERN])
        anim = ANIMATION_CLASSES.get(animation, ANIMATION_CLASSES[AnimationPreset.SMOOTH])

        # Auto-select variants based on style
        variants = section_variants or self._auto_select_variants(spec, style)

        # Glassmorphism auto-detection
        glass = tokens.get("glass_effect", False)
        if style == StylePreset.GLASSMORPHISM:
            glass = True

        design = DesignSpec(
            style_preset=style,
            animation_preset=animation,
            content_tone=content_tone,
            button_style=tokens["button_style"],
            card_style=tokens["card_style"],
            spacing_scale=tokens["spacing_scale"],
            container_max_width=tokens["container_max_width"],
            border_radius=tokens["border_radius"],
            elevation=tokens["elevation"],
            glass_effect=glass,
            gradient_enabled=tokens.get("gradient_enabled", True),
            section_variants=variants,
            icon_pack=tokens.get("icon_pack", "lucide"),
            image_style=tokens.get("image_style", "editorial"),
        )

        logger.debug(
            f"DesignResolver: style={style.value} animation={animation.value} "
            f"variants={len(variants)} glass={glass}"
        )
        return design

    def _auto_select_variants(
        self,
        spec: WebsiteSpec,
        style: StylePreset,
    ) -> dict[str, str]:
        """
        Auto-select component variants based on style preset.

        Premium styles get premium variants.
        Minimal styles get clean variants.
        """
        variants: dict[str, str] = {}

        # Hero variant selection
        if style in (StylePreset.APPLE, StylePreset.STRIPE, StylePreset.LUXURY):
            variants["Hero"] = "centered"
        elif style in (StylePreset.LINEAR, StylePreset.VERCEL):
            variants["Hero"] = "split"
        elif style == StylePreset.CYBERPUNK:
            variants["Hero"] = "glitch"
        elif style == StylePreset.BRUTALIST:
            variants["Hero"] = "bold"
        else:
            variants["Hero"] = "default"

        # Pricing variant
        if style in (StylePreset.STRIPE, StylePreset.MODERN, StylePreset.GLASSMORPHISM):
            variants["Pricing"] = "toggle"
        else:
            variants["Pricing"] = "default"

        # Navbar variant
        if style in (StylePreset.MINIMAL, StylePreset.NOTION):
            variants["Navbar"] = "simple"
        elif style in (StylePreset.GLASSMORPHISM, StylePreset.LINEAR):
            variants["Navbar"] = "blur"
        else:
            variants["Navbar"] = "default"

        # FAQ variant
        variants["FAQ"] = "accordion"

        # Footer variant
        if style in (StylePreset.MINIMAL, StylePreset.NOTION):
            variants["Footer"] = "simple"
        else:
            variants["Footer"] = "columns"

        return variants

    def get_animation_classes(self, preset: AnimationPreset) -> dict[str, str]:
        """Get animation CSS classes for a preset."""
        return ANIMATION_CLASSES.get(preset, ANIMATION_CLASSES[AnimationPreset.SMOOTH])
