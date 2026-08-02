"""
ai/planner/planner.py — Module 2: AIPlanner

The planner is the ARCHITECT. It decides:
  - Which components to include
  - In what order
  - What variant to use

The Planner owns STRATEGY. The SpecBuilder owns DATA.

Currently: Rule-based.
Future: Can be upgraded to LLM-powered planning without changing the interface.

Usage:
    planner = AIPlanner()
    plan = planner.plan(analysis_result)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from schemas.generation import (
    ComponentPlan,
    ComponentType,
    GenerationPlan,
    PromptAnalysisResult,
    WebsiteType,
)

if TYPE_CHECKING:
    from schemas.generation import GenerationRequest


# ── Default Component Blueprints ─────────────────────────────────────────────
# Each website type has a default component layout.
# The planner selects the blueprint, then overlays user-requested components.

WEBSITE_BLUEPRINTS: dict[WebsiteType, list[ComponentType]] = {
    WebsiteType.LANDING: [
        ComponentType.NAVBAR,
        ComponentType.HERO,
        ComponentType.FEATURES,
        ComponentType.HOW_IT_WORKS,
        ComponentType.CTA,
        ComponentType.FAQ,
        ComponentType.FOOTER,
    ],
    WebsiteType.SAAS: [
        ComponentType.NAVBAR,
        ComponentType.HERO,
        ComponentType.LOGOS,
        ComponentType.FEATURES,
        ComponentType.HOW_IT_WORKS,
        ComponentType.PRICING,
        ComponentType.TESTIMONIALS,
        ComponentType.FAQ,
        ComponentType.CTA,
        ComponentType.FOOTER,
    ],
    WebsiteType.PORTFOLIO: [
        ComponentType.NAVBAR,
        ComponentType.HERO,
        ComponentType.ABOUT,
        ComponentType.SKILLS,
        ComponentType.PROJECTS,
        ComponentType.TESTIMONIALS,
        ComponentType.CONTACT,
        ComponentType.FOOTER,
    ],
    WebsiteType.BLOG: [
        ComponentType.NAVBAR,
        ComponentType.HERO,
        ComponentType.BLOG_POSTS,
        ComponentType.NEWSLETTER,
        ComponentType.FOOTER,
    ],
    WebsiteType.ECOMMERCE: [
        ComponentType.NAVBAR,
        ComponentType.HERO,
        ComponentType.FEATURES,
        ComponentType.STATS,
        ComponentType.TESTIMONIALS,
        ComponentType.CTA,
        ComponentType.FOOTER,
    ],
    WebsiteType.DASHBOARD: [
        ComponentType.NAVBAR,
        ComponentType.HERO,
        ComponentType.FEATURES,
        ComponentType.STATS,
        ComponentType.PRICING,
        ComponentType.FAQ,
        ComponentType.FOOTER,
    ],
    WebsiteType.RESTAURANT: [
        ComponentType.NAVBAR,
        ComponentType.HERO,
        ComponentType.ABOUT,
        ComponentType.MENU,
        ComponentType.GALLERY,
        ComponentType.TESTIMONIALS,
        ComponentType.RESERVATION,
        ComponentType.CONTACT,
        ComponentType.FOOTER,
    ],
    WebsiteType.AGENCY: [
        ComponentType.NAVBAR,
        ComponentType.HERO,
        ComponentType.LOGOS,
        ComponentType.SERVICES,
        ComponentType.PROJECTS,
        ComponentType.TEAM,
        ComponentType.TESTIMONIALS,
        ComponentType.CTA,
        ComponentType.CONTACT,
        ComponentType.FOOTER,
    ],
    WebsiteType.STARTUP: [
        ComponentType.NAVBAR,
        ComponentType.HERO,
        ComponentType.FEATURES,
        ComponentType.HOW_IT_WORKS,
        ComponentType.PRICING,
        ComponentType.TESTIMONIALS,
        ComponentType.FAQ,
        ComponentType.CTA,
        ComponentType.FOOTER,
    ],
    WebsiteType.DOCS: [
        ComponentType.NAVBAR,
        ComponentType.HERO,
        ComponentType.FEATURES,
        ComponentType.FAQ,
        ComponentType.FOOTER,
    ],
    WebsiteType.PERSONAL: [
        ComponentType.NAVBAR,
        ComponentType.HERO,
        ComponentType.ABOUT,
        ComponentType.SKILLS,
        ComponentType.PROJECTS,
        ComponentType.CONTACT,
        ComponentType.FOOTER,
    ],
    WebsiteType.BUSINESS: [
        ComponentType.NAVBAR,
        ComponentType.HERO,
        ComponentType.SERVICES,
        ComponentType.ABOUT,
        ComponentType.STATS,
        ComponentType.TEAM,
        ComponentType.TESTIMONIALS,
        ComponentType.CONTACT,
        ComponentType.FOOTER,
    ],
    WebsiteType.UNKNOWN: [
        ComponentType.NAVBAR,
        ComponentType.HERO,
        ComponentType.FEATURES,
        ComponentType.CTA,
        ComponentType.FOOTER,
    ],
}

# Component name → ComponentType mapping (for user-requested components)
COMPONENT_NAME_MAP: dict[str, ComponentType] = {
    "Navbar":        ComponentType.NAVBAR,
    "Hero":          ComponentType.HERO,
    "Features":      ComponentType.FEATURES,
    "Pricing":       ComponentType.PRICING,
    "FAQ":           ComponentType.FAQ,
    "Footer":        ComponentType.FOOTER,
    "Contact":       ComponentType.CONTACT,
    "Gallery":       ComponentType.GALLERY,
    "Testimonials":  ComponentType.TESTIMONIALS,
    "Blog":          ComponentType.BLOG_POSTS,
    "Newsletter":    ComponentType.NEWSLETTER,
    "Team":          ComponentType.TEAM,
    "Stats":         ComponentType.STATS,
    "Services":      ComponentType.SERVICES,
    "About":         ComponentType.ABOUT,
    "CTA":           ComponentType.CTA,
    "Menu":          ComponentType.MENU,
    "Reservation":   ComponentType.RESERVATION,
    "Projects":      ComponentType.PROJECTS,
    "Skills":        ComponentType.SKILLS,
    "HowItWorks":    ComponentType.HOW_IT_WORKS,
    "Logos":         ComponentType.LOGOS,
    "BlogPosts":     ComponentType.BLOG_POSTS,
}

# Approximate token cost per component (for estimation)
TOKENS_PER_COMPONENT: dict[ComponentType, int] = {
    ComponentType.NAVBAR:       300,
    ComponentType.HERO:         500,
    ComponentType.FEATURES:     600,
    ComponentType.PRICING:      700,
    ComponentType.FAQ:          500,
    ComponentType.FOOTER:       300,
    ComponentType.CTA:          250,
    ComponentType.TESTIMONIALS: 500,
    ComponentType.ABOUT:        400,
    ComponentType.CONTACT:      350,
    ComponentType.GALLERY:      400,
    ComponentType.TEAM:         500,
    ComponentType.STATS:        350,
    ComponentType.MENU:         600,
    ComponentType.RESERVATION:  350,
    ComponentType.PROJECTS:     500,
    ComponentType.SKILLS:       350,
    ComponentType.BLOG_POSTS:   500,
    ComponentType.NEWSLETTER:   250,
    ComponentType.SERVICES:     500,
    ComponentType.HOW_IT_WORKS: 450,
    ComponentType.LOGOS:        200,
}


# ── AIPlanner ────────────────────────────────────────────────────────────────

class AIPlanner:
    """
    Module 2: Rule-based component planning.

    Takes a PromptAnalysisResult and produces a GenerationPlan.
    The plan defines what components to build and in what order.
    """

    def plan(
        self,
        analysis: PromptAnalysisResult,
        request: "Optional[GenerationRequest]" = None,
    ) -> GenerationPlan:
        """
        Build a generation plan from the analysis result.

        Strategy:
        1. Start with the blueprint for the detected website type
        2. If GenerationRequest has explicit sections, use those instead
        3. Merge any user-requested components not already in the blueprint
        4. Ensure mandatory components (Navbar, Footer) are always present
        5. Order components logically
        6. Estimate total token cost
        """
        # Phase 6: Use explicit section selections from GenerationRequest
        if request and request.sections:
            blueprint: list[ComponentType] = []
            for section_name in request.sections:
                comp_type = COMPONENT_NAME_MAP.get(section_name)
                if comp_type:
                    blueprint.append(comp_type)
        else:
            # Step 1: Get base blueprint
            blueprint = list(
                WEBSITE_BLUEPRINTS.get(analysis.website_type, WEBSITE_BLUEPRINTS[WebsiteType.LANDING])
            )

        # Step 2: Merge user-requested components from prompt analysis
        for comp_name in analysis.requested_components:
            comp_type = COMPONENT_NAME_MAP.get(comp_name)
            if comp_type and comp_type not in blueprint:
                # Insert before Footer (last item) if present
                if blueprint and blueprint[-1] == ComponentType.FOOTER:
                    blueprint.insert(-1, comp_type)
                else:
                    blueprint.append(comp_type)

        # Step 3: Ensure mandatory components
        if ComponentType.NAVBAR not in blueprint:
            blueprint.insert(0, ComponentType.NAVBAR)
        if ComponentType.FOOTER not in blueprint:
            blueprint.append(ComponentType.FOOTER)

        # Step 4: Build ordered ComponentPlan list
        components: list[ComponentPlan] = []
        for i, comp_type in enumerate(blueprint):
            components.append(
                ComponentPlan(
                    type=comp_type,
                    order=i,
                    variant="default",
                )
            )

        # Step 5: Estimate tokens
        total_tokens = sum(
            TOKENS_PER_COMPONENT.get(c.type, 400) for c in components
        )

        # Build strategy notes
        strategy_parts: list[str] = [
            f"Blueprint: {analysis.website_type.value}",
        ]
        if analysis.requested_components:
            strategy_parts.append(f"User requested: {', '.join(analysis.requested_components)}")
        if analysis.industry != "general":
            strategy_parts.append(f"Industry context: {analysis.industry}")

        return GenerationPlan(
            website_type=analysis.website_type,
            industry=analysis.industry,
            components=components,
            total_components=len(components),
            estimated_tokens=total_tokens,
            strategy_notes=" | ".join(strategy_parts),
        )
