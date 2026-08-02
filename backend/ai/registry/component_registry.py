"""
ai/registry/component_registry.py — Module 5: ComponentRegistry

The registry pattern replaces ALL hardcoded component checks.

Instead of:
    if component == "Hero":
        generate_hero()
    elif component == "Pricing":
        generate_pricing()
    ...

We use:
    generator = registry.get("Hero")
    html = await generator.generate(spec, theme)

Architecture:
    - BaseComponentGenerator: Abstract interface for all generators
    - ComponentRegistry: Maps ComponentType → generator instance
    - Auto-registration: generators register themselves at import time

No hardcoded `if component == 'X'` anywhere in the codebase.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from schemas.generation import ComponentSpec, ComponentType

if TYPE_CHECKING:
    from ai.builders.theme_engine import ResolvedTheme
    from ai.providers.base import BaseProvider, GenerationConfig

logger = logging.getLogger("ai-site-gen")


# ── Base Component Generator ─────────────────────────────────────────────────

class BaseComponentGenerator(ABC):
    """
    Abstract base for all component generators.

    Each component type has exactly one generator.
    Generators are stateless — all context comes through method args.

    Subclass contract:
        1. Set `component_type` class attribute
        2. Implement `generate()` — returns HTML string
        3. Implement `build_prompt()` — returns the LLM prompt for this component
    """
    component_type: ComponentType

    @abstractmethod
    async def generate(
        self,
        spec: ComponentSpec,
        theme: "ResolvedTheme",
        provider: "BaseProvider",
        config: "GenerationConfig",
    ) -> str:
        """
        Generate HTML for this component.

        Args:
            spec: Component specification with props
            theme: Resolved theme with design tokens
            provider: LLM provider to call
            config: Generation config (model, temperature, etc.)

        Returns:
            Raw HTML string for this component
        """
        ...

    def build_prompt(self, spec: ComponentSpec, theme: "ResolvedTheme") -> str:
        """
        Build the LLM prompt for generating this component.

        Default implementation creates a structured prompt.
        Override for component-specific prompt engineering.
        """
        props_str = "\n".join(f"  - {k}: {v}" for k, v in spec.props.items())

        return f"""Generate a single {spec.type.value} section as clean HTML using Tailwind CSS.

Component: {spec.type.value}
Variant: {spec.variant}
Theme Mode: {theme.mode.value if hasattr(theme.mode, 'value') else theme.mode}
Tone: {theme.tone.value if hasattr(theme.tone, 'value') else theme.tone}
Primary Color: {theme.colors.primary}
Background: {theme.colors.background}
Text Color: {theme.colors.text_primary}

Props:
{props_str}

RULES:
1. Return ONLY the HTML section element. No wrapper html/body/head tags.
2. Use Tailwind CSS utility classes.
3. Use inline styles for custom colors: style="color:{theme.colors.primary}"
4. Make it responsive (mobile-first).
5. Use realistic, professional content based on the props.
6. Make the design premium, polished, and modern.
7. Do NOT include <script> tags.
8. Start with a <section> or <nav> or <footer> tag immediately.
"""

    async def _call_llm(
        self,
        prompt: str,
        provider: "BaseProvider",
        config: "GenerationConfig",
    ) -> str:
        """Call the LLM provider and return the full response text."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an elite frontend engineer. Return ONLY clean HTML "
                    "using Tailwind CSS. No markdown, no code fences, no commentary. "
                    "Start with a valid HTML tag immediately."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        # Use non-streaming for individual components (simpler, more reliable)
        result = await provider.generate(messages, config)
        return result.strip()

    def _fallback_html(self, spec: ComponentSpec, theme: "ResolvedTheme") -> str:
        """Generate minimal fallback HTML if LLM fails."""
        return (
            f'<section class="py-20 px-6" style="background:{theme.colors.surface};color:{theme.colors.text_primary}">'
            f'<div class="max-w-7xl mx-auto text-center">'
            f'<h2 class="text-3xl font-bold mb-4">{spec.props.get("title", spec.type.value)}</h2>'
            f'<p class="text-lg opacity-70">Content is being generated...</p>'
            f'</div></section>'
        )


# ── Component Registry ───────────────────────────────────────────────────────

class ComponentRegistry:
    """
    Module 5: Maps ComponentType → BaseComponentGenerator.

    Usage:
        registry = ComponentRegistry()
        registry.register(HeroGenerator())
        registry.register(NavbarGenerator())

        generator = registry.get(ComponentType.HERO)
        html = await generator.generate(spec, theme, provider, config)
    """

    def __init__(self) -> None:
        self._generators: dict[ComponentType, BaseComponentGenerator] = {}

    def register(self, generator: BaseComponentGenerator) -> None:
        """Register a component generator."""
        if generator.component_type in self._generators:
            logger.warning(
                f"Overwriting generator for {generator.component_type.value}"
            )
        self._generators[generator.component_type] = generator
        logger.debug(f"Registered generator: {generator.component_type.value}")

    def get(self, component_type: ComponentType) -> BaseComponentGenerator | None:
        """Get the generator for a component type. Returns None if not found."""
        return self._generators.get(component_type)

    def has(self, component_type: ComponentType) -> bool:
        """Check if a generator is registered for this type."""
        return component_type in self._generators

    @property
    def registered_types(self) -> list[ComponentType]:
        """List all registered component types."""
        return list(self._generators.keys())

    @property
    def count(self) -> int:
        return len(self._generators)

    async def generate_component(
        self,
        spec: ComponentSpec,
        theme: "ResolvedTheme",
        provider: "BaseProvider",
        config: "GenerationConfig",
    ) -> str:
        """
        Generate HTML for a component using its registered generator.
        Falls back to a minimal section if no generator is registered.
        """
        generator = self.get(spec.type)
        if generator is None:
            logger.warning(
                f"No generator registered for {spec.type.value}; using fallback"
            )
            return self._generic_fallback(spec, theme)

        try:
            return await generator.generate(spec, theme, provider, config)
        except Exception as exc:
            logger.error(
                f"Generator failed for {spec.type.value}: {exc}", exc_info=True
            )
            return generator._fallback_html(spec, theme)

    def _generic_fallback(self, spec: ComponentSpec, theme: "ResolvedTheme") -> str:
        """Generic fallback for unregistered component types."""
        title = spec.props.get("title", spec.type.value)
        return (
            f'<section class="py-16 px-6" style="background:{theme.colors.surface};color:{theme.colors.text_primary}">'
            f'<div class="max-w-7xl mx-auto text-center">'
            f'<h2 class="text-3xl font-bold mb-4">{title}</h2>'
            f'<p class="opacity-60">This section is ready for content.</p>'
            f'</div></section>'
        )
