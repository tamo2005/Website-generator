"""
ai/planner/spec_builder.py — Module 3: SpecBuilder

Converts GenerationPlan + PromptAnalysisResult → WebsiteSpec

The SpecBuilder owns DATA. The Planner owns STRATEGY.

WebsiteSpec is the SINGLE SOURCE OF TRUTH.
Once built, the spec drives everything downstream:
  - ThemeEngine reads theme preferences from the spec
  - ComponentRegistry uses component list from the spec
  - HTMLBuilder assembles based on the spec's page structure

Usage:
    builder = SpecBuilder()
    spec = builder.build(analysis, plan)
"""
from __future__ import annotations

from schemas.generation import (
    ComponentPlan,
    ComponentSpec,
    ComponentType,
    GenerationPlan,
    PageSpec,
    PromptAnalysisResult,
    ThemeSpec,
    WebsiteSpec,
)


# ── Default Props per Component ──────────────────────────────────────────────
# These provide realistic placeholder content so components aren't empty.
# The LLM will override these — but if it fails, the defaults are usable.

def _default_props(comp_type: ComponentType, analysis: PromptAnalysisResult) -> dict:
    """Generate sensible default props for a component based on context."""
    brand = analysis.brand_name or "Acme"
    industry = analysis.industry.replace("_", " ").title()

    defaults: dict[ComponentType, dict] = {
        ComponentType.NAVBAR: {
            "brand_name": brand,
            "links": ["Features", "Pricing", "About", "Contact"],
            "cta_text": "Get Started",
        },
        ComponentType.HERO: {
            "headline": f"Build the Future with {brand}",
            "subheadline": f"The modern platform for {industry.lower()} innovation.",
            "cta_primary": "Get Started Free",
            "cta_secondary": "Learn More",
        },
        ComponentType.FEATURES: {
            "title": "Why Choose Us",
            "features": [
                {"name": "Lightning Fast", "description": "Optimized for speed and performance."},
                {"name": "Enterprise Security", "description": "Bank-grade encryption and compliance."},
                {"name": "24/7 Support", "description": "Round-the-clock expert assistance."},
            ],
        },
        ComponentType.PRICING: {
            "title": "Simple, Transparent Pricing",
            "plans": [
                {"name": "Starter", "price": "$9", "period": "/mo", "features": ["5 Projects", "Basic Analytics", "Email Support"]},
                {"name": "Pro", "price": "$29", "period": "/mo", "features": ["Unlimited Projects", "Advanced Analytics", "Priority Support"], "highlighted": True},
                {"name": "Enterprise", "price": "$99", "period": "/mo", "features": ["Custom Solutions", "Dedicated Account Manager", "SLA Guarantee"]},
            ],
        },
        ComponentType.FAQ: {
            "title": "Frequently Asked Questions",
            "items": [
                {"q": f"What is {brand}?", "a": f"{brand} is a modern platform designed for {industry.lower()} professionals."},
                {"q": "How do I get started?", "a": "Sign up for a free account and follow our quick-start guide."},
                {"q": "Is there a free trial?", "a": "Yes! We offer a 14-day free trial with no credit card required."},
                {"q": "Can I cancel anytime?", "a": "Absolutely. No lock-in contracts, cancel with one click."},
            ],
        },
        ComponentType.FOOTER: {
            "brand_name": brand,
            "columns": [
                {"title": "Product", "links": ["Features", "Pricing", "Changelog"]},
                {"title": "Company", "links": ["About", "Blog", "Careers"]},
                {"title": "Support", "links": ["Help Center", "Contact", "Status"]},
            ],
            "copyright_year": "2025",
        },
        ComponentType.CTA: {
            "headline": "Ready to Get Started?",
            "description": f"Join thousands of {industry.lower()} professionals using {brand}.",
            "button_text": "Start Free Trial",
        },
        ComponentType.TESTIMONIALS: {
            "title": "Loved by Teams Worldwide",
            "testimonials": [
                {"name": "Sarah Chen", "role": "CTO, TechFlow", "text": f"{brand} transformed how our team operates."},
                {"name": "Marcus Johnson", "role": "Head of Product, Datawise", "text": "The best investment we've made this year."},
                {"name": "Elena Petrov", "role": "Founder, Bright Labs", "text": "Incredible product. Incredible team."},
            ],
        },
        ComponentType.ABOUT: {
            "title": f"About {brand}",
            "description": f"We're a passionate team building the future of {industry.lower()}.",
            "mission": "Our mission is to make powerful tools accessible to everyone.",
        },
        ComponentType.CONTACT: {
            "title": "Get in Touch",
            "description": "Have questions? We'd love to hear from you.",
            "email": f"hello@{brand.lower().replace(' ', '')}.com",
        },
        ComponentType.GALLERY: {
            "title": "Our Work",
            "items_count": 6,
        },
        ComponentType.TEAM: {
            "title": "Meet the Team",
            "members": [
                {"name": "Alex Rivera", "role": "CEO & Founder"},
                {"name": "Jordan Lee", "role": "CTO"},
                {"name": "Sam Patel", "role": "Head of Design"},
                {"name": "Morgan Chen", "role": "Lead Engineer"},
            ],
        },
        ComponentType.STATS: {
            "title": "By the Numbers",
            "stats": [
                {"value": "10K+", "label": "Customers"},
                {"value": "99.9%", "label": "Uptime"},
                {"value": "50M+", "label": "Requests/Day"},
                {"value": "4.9★", "label": "Rating"},
            ],
        },
        ComponentType.MENU: {
            "title": "Our Menu",
            "categories": [
                {"name": "Starters", "items": [{"name": "Bruschetta", "price": "$12"}, {"name": "Soup of the Day", "price": "$9"}]},
                {"name": "Mains", "items": [{"name": "Grilled Salmon", "price": "$28"}, {"name": "Pasta Carbonara", "price": "$22"}]},
            ],
        },
        ComponentType.RESERVATION: {
            "title": "Reserve a Table",
            "description": "Book your dining experience with us.",
        },
        ComponentType.PROJECTS: {
            "title": "Featured Projects",
            "projects": [
                {"name": "Project Alpha", "description": "A complete redesign of the platform.", "tags": ["Design", "Development"]},
                {"name": "Project Beta", "description": "Mobile-first e-commerce experience.", "tags": ["Mobile", "UX"]},
                {"name": "Project Gamma", "description": "Data dashboard for enterprise clients.", "tags": ["Analytics", "Enterprise"]},
            ],
        },
        ComponentType.SKILLS: {
            "title": "Skills & Expertise",
            "skills": ["Python", "TypeScript", "React", "Node.js", "AWS", "Docker"],
        },
        ComponentType.BLOG_POSTS: {
            "title": "Latest Articles",
            "posts": [
                {"title": "Getting Started Guide", "excerpt": "Everything you need to know.", "date": "Jan 2025"},
                {"title": "Best Practices", "excerpt": "Tips from our engineering team.", "date": "Feb 2025"},
                {"title": "2025 Roadmap", "excerpt": "What's coming next.", "date": "Mar 2025"},
            ],
        },
        ComponentType.NEWSLETTER: {
            "title": "Stay Updated",
            "description": "Get the latest news and updates delivered to your inbox.",
            "button_text": "Subscribe",
        },
        ComponentType.SERVICES: {
            "title": "Our Services",
            "services": [
                {"name": "Web Development", "description": "Custom websites and web applications."},
                {"name": "Mobile Apps", "description": "iOS and Android applications."},
                {"name": "Cloud Infrastructure", "description": "Scalable cloud solutions."},
            ],
        },
        ComponentType.HOW_IT_WORKS: {
            "title": "How It Works",
            "steps": [
                {"step": "1", "title": "Sign Up", "description": "Create your free account in seconds."},
                {"step": "2", "title": "Configure", "description": "Set up your workspace and preferences."},
                {"step": "3", "title": "Launch", "description": "Go live and start seeing results."},
            ],
        },
        ComponentType.LOGOS: {
            "title": "Trusted By",
            "logos": ["TechCorp", "InnovateLabs", "DataStream", "CloudFirst", "NextGen"],
        },
    }

    return defaults.get(comp_type, {})


# ── SpecBuilder ──────────────────────────────────────────────────────────────

class SpecBuilder:
    """
    Module 3: Converts GenerationPlan → WebsiteSpec.

    WebsiteSpec is the single source of truth.
    """

    def build(
        self,
        analysis: PromptAnalysisResult,
        plan: GenerationPlan,
    ) -> WebsiteSpec:
        """Build a complete WebsiteSpec from analysis + plan."""

        # Build component specs with default props
        components: list[ComponentSpec] = []
        for comp_plan in plan.components:
            components.append(
                ComponentSpec(
                    type=comp_plan.type,
                    order=comp_plan.order,
                    variant=comp_plan.variant,
                    props=_default_props(comp_plan.type, analysis),
                )
            )

        # Build theme spec
        theme = ThemeSpec(
            mode=analysis.theme,
            tone=analysis.tone,
        )

        # Build the main page
        brand = analysis.brand_name or "My Website"
        page = PageSpec(
            path="/",
            title=brand,
            components=components,
        )

        # Build meta description
        meta = (
            f"{brand} — a {analysis.tone.value}, {analysis.theme.value}-themed "
            f"{analysis.website_type.value} website for the {analysis.industry} industry."
        )

        return WebsiteSpec(
            site_name=brand,
            industry=analysis.industry,
            website_type=analysis.website_type,
            theme=theme,
            pages=[page],
            meta_description=meta,
            pipeline_version="V1",
        )
