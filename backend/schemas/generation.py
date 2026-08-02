"""
schemas/generation.py — Core Pydantic schemas for the AI generation pipeline

These are the data contracts that flow through the pipeline:
  PromptAnalysisResult → GenerationPlan → WebsiteSpec → ComponentSpec

WebsiteSpec is the SINGLE SOURCE OF TRUTH for a website. HTML is a derived artifact.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Website Types ────────────────────────────────────────────────────────────

class WebsiteType(str, Enum):
    LANDING     = "landing"
    PORTFOLIO   = "portfolio"
    BLOG        = "blog"
    ECOMMERCE   = "ecommerce"
    DASHBOARD   = "dashboard"
    SAAS        = "saas"
    RESTAURANT  = "restaurant"
    AGENCY      = "agency"
    STARTUP     = "startup"
    DOCS        = "docs"
    PERSONAL    = "personal"
    BUSINESS    = "business"
    UNKNOWN     = "unknown"


class ComponentType(str, Enum):
    NAVBAR        = "Navbar"
    HERO          = "Hero"
    FEATURES      = "Features"
    PRICING       = "Pricing"
    FAQ           = "FAQ"
    FOOTER        = "Footer"
    CTA           = "CTA"
    TESTIMONIALS  = "Testimonials"
    ABOUT         = "About"
    CONTACT       = "Contact"
    GALLERY       = "Gallery"
    TEAM          = "Team"
    STATS         = "Stats"
    MENU          = "Menu"            # Restaurant menu
    RESERVATION   = "Reservation"     # Restaurant booking
    PROJECTS      = "Projects"        # Portfolio projects grid
    SKILLS        = "Skills"          # Portfolio skills section
    BLOG_POSTS    = "BlogPosts"
    NEWSLETTER    = "Newsletter"
    SERVICES      = "Services"
    HOW_IT_WORKS  = "HowItWorks"
    LOGOS         = "Logos"           # Partner/client logos


class ThemeMode(str, Enum):
    DARK  = "dark"
    LIGHT = "light"
    AUTO  = "auto"


class ToneStyle(str, Enum):
    MODERN       = "modern"
    MINIMAL      = "minimal"
    BOLD         = "bold"
    PLAYFUL      = "playful"
    CORPORATE    = "corporate"
    ELEGANT      = "elegant"
    TECHY        = "techy"
    CREATIVE     = "creative"


# ── Module 1: Prompt Analysis Result ─────────────────────────────────────────

class PromptAnalysisResult(BaseModel):
    """Output of the PromptAnalyzer. No LLM — pure deterministic rules."""
    website_type: WebsiteType = WebsiteType.LANDING
    industry: str = "general"
    theme: ThemeMode = ThemeMode.DARK
    tone: ToneStyle = ToneStyle.MODERN
    requested_components: list[str] = Field(default_factory=list)
    detected_keywords: list[str] = Field(default_factory=list)
    brand_name: Optional[str] = None
    color_hint: Optional[str] = None    # e.g. "blue", "gradient", "neon"
    has_pricing: bool = False
    has_contact: bool = False
    has_gallery: bool = False
    has_blog: bool = False
    prompt_complexity: str = "standard"  # "simple" | "standard" | "complex"


# ── Module 2: Generation Plan ────────────────────────────────────────────────

class ComponentPlan(BaseModel):
    """A single component in the generation plan."""
    type: ComponentType
    order: int
    variant: str = "default"   # Future: "minimal", "hero-split", "hero-centered"
    notes: Optional[str] = None


class GenerationPlan(BaseModel):
    """
    Output of the AIPlanner. Decides WHAT components to generate and in what order.
    The Planner owns strategy. The SpecBuilder owns data.
    """
    website_type: WebsiteType
    industry: str
    components: list[ComponentPlan]
    total_components: int = 0
    estimated_tokens: int = 0
    strategy_notes: str = ""


# ── Module 3: Website Specification ──────────────────────────────────────────

class ColorPalette(BaseModel):
    """Resolved color palette for the website."""
    primary: str = "#06b6d4"       # cyan-500
    secondary: str = "#8b5cf6"     # violet-500
    accent: str = "#f59e0b"        # amber-500
    background: str = "#020617"    # slate-950
    surface: str = "#0f172a"       # slate-900
    text_primary: str = "#f1f5f9"  # slate-100
    text_secondary: str = "#94a3b8" # slate-400
    border: str = "rgba(255,255,255,0.1)"


class TypographySpec(BaseModel):
    """Typography configuration."""
    heading_font: str = "Inter"
    body_font: str = "Inter"
    base_size: str = "16px"


class ThemeSpec(BaseModel):
    """Full theme specification for the website."""
    mode: ThemeMode = ThemeMode.DARK
    tone: ToneStyle = ToneStyle.MODERN
    colors: ColorPalette = Field(default_factory=ColorPalette)
    typography: TypographySpec = Field(default_factory=TypographySpec)
    border_radius: str = "0.75rem"
    glass_effect: bool = True


class ComponentSpec(BaseModel):
    """Specification for a single component to be generated."""
    type: ComponentType
    order: int
    variant: str = "default"
    props: dict = Field(default_factory=dict)  # Component-specific data (title, items, etc.)


class PageSpec(BaseModel):
    """A single page in the website."""
    path: str = "/"
    title: str = "Home"
    components: list[ComponentSpec] = Field(default_factory=list)


class WebsiteSpec(BaseModel):
    """
    THE SINGLE SOURCE OF TRUTH for a website.

    HTML is a derived artifact generated from this spec.
    This spec can be:
      - Stored as JSON in the database
      - Used to regenerate HTML at any time
      - Diffed for partial regeneration
      - Exported to different frameworks (React, Vue) in Phase 3+
    """
    site_name: str = "My Website"
    industry: str = "general"
    website_type: WebsiteType = WebsiteType.LANDING
    theme: ThemeSpec = Field(default_factory=ThemeSpec)
    pages: list[PageSpec] = Field(default_factory=list)
    meta_description: str = ""
    pipeline_version: str = "V1"

    @property
    def all_components(self) -> list[ComponentSpec]:
        """Flatten all components across all pages."""
        result = []
        for page in self.pages:
            result.extend(page.components)
        return result

    @property
    def component_types(self) -> list[str]:
        """Return ordered list of component type names."""
        return [c.type.value for c in self.all_components]
