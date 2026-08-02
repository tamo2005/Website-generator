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


# ── Phase 6: Style, Animation, Content Presets ───────────────────────────────

class StylePreset(str, Enum):
    """Visual design language presets. Each maps to concrete design tokens."""
    MODERN         = "modern"
    MINIMAL        = "minimal"
    GLASSMORPHISM  = "glassmorphism"
    CORPORATE      = "corporate"
    LUXURY         = "luxury"
    CYBERPUNK      = "cyberpunk"
    BRUTALIST      = "brutalist"
    APPLE          = "apple"        # Clean, spacious, SF-Pro inspired
    STRIPE         = "stripe"       # Gradient-heavy, bold typography
    LINEAR         = "linear"       # Dark, refined, geometric
    NOTION         = "notion"       # Light, serif-accented, warm
    VERCEL         = "vercel"       # Monochrome, sharp, developer-focused


class AnimationPreset(str, Enum):
    NONE    = "none"
    MINIMAL = "minimal"     # Subtle fades only
    SMOOTH  = "smooth"      # Fade + slide + scale
    FANCY   = "fancy"       # Parallax, stagger, morphs


class ContentTone(str, Enum):
    PROFESSIONAL = "professional"
    MARKETING    = "marketing"
    CASUAL       = "casual"
    MINIMAL_COPY = "minimal"
    LUXURY       = "luxury"


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


# ── Phase 6: DesignSpec ──────────────────────────────────────────────────────

class DesignSpec(BaseModel):
    """
    Phase 6: Separates WHAT the website is (WebsiteSpec) from HOW it looks.

    WebsiteSpec → content, structure, components
    DesignSpec  → visual language, spacing, animation, variants

    This single decision makes it trivially easy to:
      - Swap design systems without changing content
      - Add future themes
      - A/B test visual styles
    """
    style_preset: StylePreset = StylePreset.MODERN
    animation_preset: AnimationPreset = AnimationPreset.SMOOTH
    content_tone: ContentTone = ContentTone.PROFESSIONAL

    # Layout tokens
    button_style: str = "rounded-xl px-6 py-3"  # Tailwind classes
    card_style: str = "rounded-2xl border"       # Card appearance
    spacing_scale: str = "8px"                    # Base spacing unit
    container_max_width: str = "max-w-7xl"       # Content width

    # Visual tokens
    border_radius: str = "0.75rem"
    elevation: str = "shadow-lg"                  # Default shadow
    glass_effect: bool = False                    # Backdrop blur
    gradient_enabled: bool = True

    # Component variant selections
    section_variants: dict[str, str] = Field(
        default_factory=dict,
        description="Component type → variant name, e.g. {'Hero': 'split', 'Pricing': 'toggle'}",
    )

    # Asset preferences
    icon_pack: str = "lucide"                     # lucide, heroicons, custom-svg
    image_style: str = "editorial"                # editorial, abstract, photo, illustration


class ImageCounts(BaseModel):
    """How many images to use in each section."""
    hero_images: int = Field(default=1, ge=0, le=5)
    gallery_images: int = Field(default=6, ge=0, le=20)
    team_members: int = Field(default=4, ge=0, le=12)
    logos: int = Field(default=6, ge=0, le=16)
    testimonial_avatars: int = Field(default=3, ge=0, le=10)


class GenerationRequest(BaseModel):
    """
    Phase 6: Enriched generation payload from the frontend configuration wizard.

    Instead of just {"prompt": "..."}, the frontend sends:
    {
      "prompt": "Create AI Startup",
      "website_type": "saas",
      "theme": "dark",
      "style": "linear",
      "animations": "smooth",
      "color": "purple",
      "sections": ["Hero", "Features", "Pricing", "FAQ", "Footer"],
      "image_counts": {"hero_images": 2, "gallery_images": 6},
      "content_tone": "professional"
    }
    """
    prompt: str = Field(min_length=3, max_length=8000)

    # Optional overrides — if not provided, the analyzer detects them
    website_type: Optional[WebsiteType] = None
    theme: Optional[ThemeMode] = None
    style: Optional[StylePreset] = None
    color: Optional[str] = None                   # Color hint: "blue", "purple", etc.
    animations: Optional[AnimationPreset] = None
    content_tone: Optional[ContentTone] = None
    sections: Optional[list[str]] = None          # Explicit section selection
    image_counts: Optional[ImageCounts] = None
    brand_name: Optional[str] = None
