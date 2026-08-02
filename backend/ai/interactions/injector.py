"""
ai/interactions/injector.py — Phase 6: Interaction Injector

Determines which JavaScript interaction modules to inject based on
the website's components, then produces a single <script> block.

Architecture:
    WebsiteSpec + DesignSpec
        ↓
    InteractionInjector
        ↓
    <script> block (appended to </body>)

Usage:
    injector = InteractionInjector()
    script_block = injector.inject(spec, design)
    # Returns: <script>/* faq */.../* navbar */...</script>
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai.interactions.library import InteractionLibrary
from schemas.generation import AnimationPreset, ComponentType, WebsiteSpec

if TYPE_CHECKING:
    from schemas.generation import DesignSpec

logger = logging.getLogger("ai-site-gen")


# ── Component → Required Interactions ────────────────────────────────────────

COMPONENT_INTERACTIONS: dict[ComponentType, list[str]] = {
    ComponentType.NAVBAR:        ["navbar", "scroll"],
    ComponentType.HERO:          ["typing"],
    ComponentType.FAQ:           ["faq"],
    ComponentType.PRICING:       ["pricing"],
    ComponentType.GALLERY:       ["gallery"],
    ComponentType.TESTIMONIALS:  ["carousel"],
    ComponentType.STATS:         ["counter"],
    ComponentType.NEWSLETTER:    ["newsletter"],
    ComponentType.CONTACT:       ["newsletter"],  # Reuse form validation
}


class InteractionInjector:
    """
    Phase 6: Determines and bundles JavaScript interactions.

    Analyzes the WebsiteSpec to determine which components are present,
    then bundles only the required interaction scripts.
    """

    def inject(
        self,
        spec: WebsiteSpec,
        design: "DesignSpec | None" = None,
    ) -> str:
        """
        Produce a <script> block with all required interactions.

        Returns empty string if no interactions are needed.
        """
        needed = self._determine_interactions(spec, design)
        if not needed:
            return ""

        bundle = InteractionLibrary.get_bundle(sorted(needed))
        if not bundle:
            return ""

        logger.debug(f"InteractionInjector: injecting {len(needed)} scripts: {sorted(needed)}")

        return (
            "\n<!-- Interaction Scripts (Phase 6) -->\n"
            f"<script>\n{bundle}\n</script>\n"
        )

    def _determine_interactions(
        self,
        spec: WebsiteSpec,
        design: "DesignSpec | None" = None,
    ) -> set[str]:
        """Determine which interaction scripts are needed."""
        needed: set[str] = set()

        # Map component types to their required interactions
        for component in spec.all_components:
            interactions = COMPONENT_INTERACTIONS.get(component.type, [])
            needed.update(interactions)

        # Always add reveal-on-scroll unless animations are disabled
        if design is None or design.animation_preset != AnimationPreset.NONE:
            needed.add("reveal")

        # Always add smooth scroll if there's a navbar
        component_types = {c.type for c in spec.all_components}
        if ComponentType.NAVBAR in component_types:
            needed.add("scroll")

        return needed

    def list_injected(self, spec: WebsiteSpec, design: "DesignSpec | None" = None) -> list[str]:
        """List which scripts would be injected (for debugging/logging)."""
        return sorted(self._determine_interactions(spec, design))
