"""
ai/registry/generators/all_generators.py — Module 6: Component Generators

Each generator subclasses BaseComponentGenerator and provides
component-specific prompt engineering for optimal LLM output.

All generators:
  1. Build a targeted prompt using component props + theme
  2. Call the LLM
  3. Clean and return the HTML
  4. Provide a rich fallback if LLM fails

Registered component types:
  Navbar, Hero, Features, Pricing, FAQ, Footer, CTA, Testimonials,
  About, Contact, Gallery, Team, Stats, Menu, Reservation, Projects,
  Skills, BlogPosts, Newsletter, Services, HowItWorks, Logos
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from schemas.generation import ComponentSpec, ComponentType
from ai.registry.component_registry import BaseComponentGenerator

if TYPE_CHECKING:
    from ai.builders.theme_engine import ResolvedTheme
    from ai.providers.base import BaseProvider, GenerationConfig

logger = logging.getLogger("ai-site-gen")


# ── HTML Cleaning Helper ─────────────────────────────────────────────────────

def _clean_html(raw: str) -> str:
    """Strip markdown fences, think blocks, and leading noise from LLM output."""
    # Remove code fences
    raw = re.sub(r"```(?:html|HTML)?\s*\n?", "", raw)
    raw = re.sub(r"```\s*$", "", raw)
    # Remove think blocks
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.IGNORECASE | re.DOTALL)
    raw = re.sub(r"<think>.*$", "", raw, flags=re.IGNORECASE | re.DOTALL)
    # Trim to first HTML tag
    idx = raw.find("<")
    if idx > 0:
        raw = raw[idx:]
    return raw.strip()


# ══════════════════════════════════════════════════════════════════════════════
# NAVBAR GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class NavbarGenerator(BaseComponentGenerator):
    component_type = ComponentType.NAVBAR

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def build_prompt(self, spec, theme) -> str:
        brand = spec.props.get("brand_name", "Brand")
        links = spec.props.get("links", ["Features", "Pricing", "About"])
        cta = spec.props.get("cta_text", "Get Started")
        return f"""Generate a modern, responsive navigation bar as HTML using Tailwind CSS.

Brand name: {brand}
Nav links: {', '.join(links)}
CTA button text: {cta}
Theme: {theme.mode.value} mode
Primary color: {theme.colors.primary}
Background: {theme.colors.background}
Text color: {theme.colors.text_primary}

Requirements:
- Sticky/fixed top navigation with backdrop blur
- Logo/brand name on the left
- Navigation links in the center
- CTA button on the right with primary color
- Mobile hamburger menu (hidden on desktop, use Tailwind responsive)
- Glass morphism effect: bg-white/5 backdrop-blur-xl border-b border-white/10
- Use <nav> tag as root element
- Smooth, premium feel
"""

    def _fallback_html(self, spec, theme) -> str:
        brand = spec.props.get("brand_name", "Brand")
        links = spec.props.get("links", ["Features", "Pricing", "About"])
        cta = spec.props.get("cta_text", "Get Started")
        links_html = "".join(
            f'<a href="#" class="text-sm hover:opacity-80 transition-opacity">{l}</a>'
            for l in links
        )
        return f"""<nav class="fixed top-0 left-0 right-0 z-50 border-b backdrop-blur-xl" style="background:rgba(2,6,23,0.8);border-color:{theme.colors.border}">
  <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
    <span class="text-lg font-bold" style="color:{theme.colors.primary}">{brand}</span>
    <div class="hidden md:flex items-center gap-8" style="color:{theme.colors.text_secondary}">{links_html}</div>
    <a href="#" class="hidden md:inline-flex px-4 py-2 rounded-lg text-sm font-medium text-white" style="background:{theme.colors.primary}">{cta}</a>
  </div>
</nav>"""


# ══════════════════════════════════════════════════════════════════════════════
# HERO GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class HeroGenerator(BaseComponentGenerator):
    component_type = ComponentType.HERO

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def build_prompt(self, spec, theme) -> str:
        headline = spec.props.get("headline", "Build Something Amazing")
        sub = spec.props.get("subheadline", "The modern platform for innovation.")
        cta1 = spec.props.get("cta_primary", "Get Started")
        cta2 = spec.props.get("cta_secondary", "Learn More")
        return f"""Generate a stunning hero section as HTML using Tailwind CSS.

Headline: {headline}
Subheadline: {sub}
Primary CTA: {cta1}
Secondary CTA: {cta2}
Theme: {theme.mode.value} mode
Primary color: {theme.colors.primary}
Secondary color: {theme.colors.secondary}
Background: {theme.colors.background}

Requirements:
- Full viewport height (min-h-screen) with centered content
- Large, bold headline (text-5xl md:text-7xl font-black)
- Subtle gradient or glow effect behind the headline
- Two CTA buttons: primary (filled) and secondary (outline)
- Floating badge/pill above headline (e.g. "Launching 2025")
- Ambient gradient orbs or decorative elements in the background
- Professional, premium feel
- Add pt-20 to account for fixed navbar
"""

    def _fallback_html(self, spec, theme) -> str:
        headline = spec.props.get("headline", "Build Something Amazing")
        sub = spec.props.get("subheadline", "The modern platform for innovation.")
        cta1 = spec.props.get("cta_primary", "Get Started")
        cta2 = spec.props.get("cta_secondary", "Learn More")
        return f"""<section class="relative min-h-screen flex items-center justify-center px-6 pt-20 overflow-hidden" style="background:{theme.colors.background};color:{theme.colors.text_primary}">
  <div class="absolute inset-0 overflow-hidden"><div class="absolute top-1/4 left-1/4 w-96 h-96 rounded-full blur-3xl opacity-20" style="background:{theme.colors.primary}"></div><div class="absolute bottom-1/4 right-1/4 w-80 h-80 rounded-full blur-3xl opacity-15" style="background:{theme.colors.secondary}"></div></div>
  <div class="relative z-10 max-w-4xl mx-auto text-center">
    <span class="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-semibold tracking-wider uppercase mb-8 border" style="color:{theme.colors.primary};border-color:{theme.colors.primary}33;background:{theme.colors.primary}15">✨ Now Available</span>
    <h1 class="text-5xl md:text-7xl font-black tracking-tight leading-tight mb-6">{headline}</h1>
    <p class="text-lg md:text-xl max-w-2xl mx-auto mb-10" style="color:{theme.colors.text_secondary}">{sub}</p>
    <div class="flex flex-col sm:flex-row items-center justify-center gap-4">
      <a href="#" class="px-8 py-3.5 rounded-xl text-base font-semibold text-white shadow-lg transition-transform hover:scale-105" style="background:{theme.colors.primary}">{cta1}</a>
      <a href="#" class="px-8 py-3.5 rounded-xl text-base font-semibold border transition-colors hover:bg-white/5" style="color:{theme.colors.text_primary};border-color:{theme.colors.border}">{cta2}</a>
    </div>
  </div>
</section>"""


# ══════════════════════════════════════════════════════════════════════════════
# FEATURES GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class FeaturesGenerator(BaseComponentGenerator):
    component_type = ComponentType.FEATURES

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def build_prompt(self, spec, theme) -> str:
        title = spec.props.get("title", "Features")
        features = spec.props.get("features", [])
        features_str = "\n".join(
            f"  - {f.get('name', 'Feature')}: {f.get('description', '')}"
            for f in features
        ) if features else "  - Use 3-4 compelling features with icons"
        return f"""Generate a features section as HTML using Tailwind CSS.

Section title: {title}
Features:
{features_str}

Theme: {theme.mode.value} mode
Primary color: {theme.colors.primary}
Surface color: {theme.colors.surface}

Requirements:
- Section heading with subtitle
- 3-column grid on desktop, 1-column on mobile
- Each feature card: icon (use emoji or SVG), title, description
- Cards with glass morphism: bg-white/5 border border-white/10 backdrop-blur
- Subtle hover effect on cards
- Professional spacing and typography
"""

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "Features")
        features = spec.props.get("features", [
            {"name": "Lightning Fast", "description": "Optimized for speed."},
            {"name": "Secure", "description": "Enterprise-grade security."},
            {"name": "Scalable", "description": "Grows with your needs."},
        ])
        cards = ""
        icons = ["⚡", "🔒", "📈", "🎯", "🚀", "💎"]
        for i, f in enumerate(features):
            icon = icons[i % len(icons)]
            cards += f"""<div class="rounded-2xl border p-6 backdrop-blur transition-all hover:scale-[1.02]" style="background:rgba(255,255,255,0.03);border-color:{theme.colors.border}">
      <div class="text-3xl mb-4">{icon}</div>
      <h3 class="text-lg font-semibold mb-2">{f.get("name", "Feature")}</h3>
      <p class="text-sm leading-relaxed" style="color:{theme.colors.text_secondary}">{f.get("description", "")}</p>
    </div>"""
        return f"""<section class="py-24 px-6" style="background:{theme.colors.background};color:{theme.colors.text_primary}">
  <div class="max-w-7xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold text-center mb-4">{title}</h2>
    <p class="text-center mb-16 max-w-2xl mx-auto" style="color:{theme.colors.text_secondary}">Everything you need to succeed</p>
    <div class="grid md:grid-cols-3 gap-6">{cards}</div>
  </div>
</section>"""


# ══════════════════════════════════════════════════════════════════════════════
# PRICING GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class PricingGenerator(BaseComponentGenerator):
    component_type = ComponentType.PRICING

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def build_prompt(self, spec, theme) -> str:
        title = spec.props.get("title", "Pricing")
        plans = spec.props.get("plans", [])
        plans_str = "\n".join(
            f"  - {p.get('name', 'Plan')}: {p.get('price', '$X')}{p.get('period', '/mo')} — {', '.join(p.get('features', []))}"
            for p in plans
        ) if plans else "  - Create 3 pricing tiers (Starter, Pro, Enterprise)"
        return f"""Generate a pricing section as HTML using Tailwind CSS.

Section title: {title}
Plans:
{plans_str}

Theme: {theme.mode.value} mode
Primary color: {theme.colors.primary}
Surface: {theme.colors.surface}

Requirements:
- 3-column pricing grid, 1-column on mobile
- Middle card (Pro) should be highlighted/recommended with primary color border
- Each card: plan name, price, period, feature list with checkmarks, CTA button
- Glass morphism cards
- "Most Popular" badge on highlighted plan
- Professional, trustworthy design
"""

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "Pricing")
        plans = spec.props.get("plans", [
            {"name": "Starter", "price": "$9", "period": "/mo", "features": ["5 Projects", "Basic Analytics"], "highlighted": False},
            {"name": "Pro", "price": "$29", "period": "/mo", "features": ["Unlimited Projects", "Advanced Analytics", "Priority Support"], "highlighted": True},
            {"name": "Enterprise", "price": "$99", "period": "/mo", "features": ["Custom Solutions", "Dedicated Manager", "SLA"], "highlighted": False},
        ])
        cards = ""
        for p in plans:
            hi = p.get("highlighted", False)
            border = f"border-color:{theme.colors.primary}" if hi else f"border-color:{theme.colors.border}"
            badge = f'<span class="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 text-xs font-bold rounded-full text-white" style="background:{theme.colors.primary}">Most Popular</span>' if hi else ""
            features_html = "".join(f'<li class="flex items-center gap-2 text-sm"><span style="color:{theme.colors.primary}">✓</span> {f}</li>' for f in p.get("features", []))
            cards += f"""<div class="relative rounded-2xl border p-8 backdrop-blur" style="background:rgba(255,255,255,0.03);{border}">
      {badge}
      <h3 class="text-xl font-bold mb-2">{p["name"]}</h3>
      <div class="flex items-baseline gap-1 mb-6"><span class="text-4xl font-black">{p["price"]}</span><span class="text-sm" style="color:{theme.colors.text_secondary}">{p.get("period", "/mo")}</span></div>
      <ul class="space-y-3 mb-8">{features_html}</ul>
      <a href="#" class="block w-full text-center py-3 rounded-xl text-sm font-semibold transition-colors" style="background:{'%s' % theme.colors.primary if hi else 'rgba(255,255,255,0.05)'};color:{'white' if hi else theme.colors.text_primary}">Get Started</a>
    </div>"""
        return f"""<section class="py-24 px-6" style="background:{theme.colors.background};color:{theme.colors.text_primary}">
  <div class="max-w-7xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold text-center mb-4">{title}</h2>
    <p class="text-center mb-16 max-w-2xl mx-auto" style="color:{theme.colors.text_secondary}">Choose the plan that fits your needs</p>
    <div class="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">{cards}</div>
  </div>
</section>"""


# ══════════════════════════════════════════════════════════════════════════════
# FAQ GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class FAQGenerator(BaseComponentGenerator):
    component_type = ComponentType.FAQ

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "FAQ")
        items = spec.props.get("items", [
            {"q": "What is this?", "a": "A modern platform for your needs."},
            {"q": "Is there a free trial?", "a": "Yes, 14 days free."},
            {"q": "Can I cancel?", "a": "Yes, anytime with no fees."},
        ])
        faqs = ""
        for item in items:
            faqs += f"""<div class="border-b py-6" style="border-color:{theme.colors.border}">
      <h3 class="text-lg font-semibold mb-2">{item["q"]}</h3>
      <p class="text-sm leading-relaxed" style="color:{theme.colors.text_secondary}">{item["a"]}</p>
    </div>"""
        return f"""<section class="py-24 px-6" style="background:{theme.colors.background};color:{theme.colors.text_primary}">
  <div class="max-w-3xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold text-center mb-16">{title}</h2>
    <div>{faqs}</div>
  </div>
</section>"""


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class FooterGenerator(BaseComponentGenerator):
    component_type = ComponentType.FOOTER

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        brand = spec.props.get("brand_name", "Brand")
        columns = spec.props.get("columns", [
            {"title": "Product", "links": ["Features", "Pricing"]},
            {"title": "Company", "links": ["About", "Blog"]},
            {"title": "Support", "links": ["Help", "Contact"]},
        ])
        cols_html = ""
        for col in columns:
            links = "".join(f'<li><a href="#" class="text-sm hover:opacity-80 transition-opacity" style="color:{theme.colors.text_secondary}">{l}</a></li>' for l in col.get("links", []))
            cols_html += f'<div><h4 class="text-sm font-semibold mb-4">{col["title"]}</h4><ul class="space-y-2">{links}</ul></div>'
        return f"""<footer class="py-16 px-6 border-t" style="background:{theme.colors.background};color:{theme.colors.text_primary};border-color:{theme.colors.border}">
  <div class="max-w-7xl mx-auto">
    <div class="grid md:grid-cols-4 gap-8 mb-12">
      <div><span class="text-xl font-bold" style="color:{theme.colors.primary}">{brand}</span><p class="mt-3 text-sm" style="color:{theme.colors.text_secondary}">Building the future, one pixel at a time.</p></div>
      {cols_html}
    </div>
    <div class="border-t pt-8 text-center text-sm" style="border-color:{theme.colors.border};color:{theme.colors.text_secondary}">© 2025 {brand}. All rights reserved.</div>
  </div>
</footer>"""


# ══════════════════════════════════════════════════════════════════════════════
# CTA GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class CTAGenerator(BaseComponentGenerator):
    component_type = ComponentType.CTA

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        headline = spec.props.get("headline", "Ready to Get Started?")
        desc = spec.props.get("description", "Join thousands of professionals.")
        btn = spec.props.get("button_text", "Start Free Trial")
        return f"""<section class="py-24 px-6" style="background:{theme.colors.surface};color:{theme.colors.text_primary}">
  <div class="max-w-4xl mx-auto text-center rounded-3xl p-12 border" style="background:rgba(255,255,255,0.03);border-color:{theme.colors.border}">
    <h2 class="text-3xl md:text-4xl font-bold mb-4">{headline}</h2>
    <p class="text-lg mb-8 max-w-xl mx-auto" style="color:{theme.colors.text_secondary}">{desc}</p>
    <a href="#" class="inline-flex px-8 py-3.5 rounded-xl text-base font-semibold text-white shadow-lg transition-transform hover:scale-105" style="background:{theme.colors.primary}">{btn}</a>
  </div>
</section>"""


# ══════════════════════════════════════════════════════════════════════════════
# TESTIMONIALS GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class TestimonialsGenerator(BaseComponentGenerator):
    component_type = ComponentType.TESTIMONIALS

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "Testimonials")
        testimonials = spec.props.get("testimonials", [
            {"name": "Sarah Chen", "role": "CTO", "text": "Incredible product."},
            {"name": "Marcus J.", "role": "PM", "text": "Best investment this year."},
            {"name": "Elena P.", "role": "Founder", "text": "Transformed our workflow."},
        ])
        cards = ""
        for t in testimonials:
            cards += f"""<div class="rounded-2xl border p-6 backdrop-blur" style="background:rgba(255,255,255,0.03);border-color:{theme.colors.border}">
      <p class="text-sm leading-relaxed mb-6" style="color:{theme.colors.text_secondary}">"{t['text']}"</p>
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold" style="background:{theme.colors.primary}22;color:{theme.colors.primary}">{t['name'][0]}</div>
        <div><p class="text-sm font-semibold">{t['name']}</p><p class="text-xs" style="color:{theme.colors.text_secondary}">{t['role']}</p></div>
      </div>
    </div>"""
        return f"""<section class="py-24 px-6" style="background:{theme.colors.background};color:{theme.colors.text_primary}">
  <div class="max-w-7xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold text-center mb-16">{title}</h2>
    <div class="grid md:grid-cols-3 gap-6">{cards}</div>
  </div>
</section>"""


# ══════════════════════════════════════════════════════════════════════════════
# ABOUT GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class AboutGenerator(BaseComponentGenerator):
    component_type = ComponentType.ABOUT

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "About Us")
        desc = spec.props.get("description", "We build innovative solutions.")
        mission = spec.props.get("mission", "Making powerful tools accessible to everyone.")
        return f"""<section class="py-24 px-6" style="background:{theme.colors.surface};color:{theme.colors.text_primary}">
  <div class="max-w-4xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold mb-6">{title}</h2>
    <p class="text-lg leading-relaxed mb-8" style="color:{theme.colors.text_secondary}">{desc}</p>
    <div class="rounded-2xl border p-8" style="background:rgba(255,255,255,0.03);border-color:{theme.colors.border}">
      <h3 class="text-xl font-semibold mb-3" style="color:{theme.colors.primary}">Our Mission</h3>
      <p class="leading-relaxed" style="color:{theme.colors.text_secondary}">{mission}</p>
    </div>
  </div>
</section>"""


# ══════════════════════════════════════════════════════════════════════════════
# CONTACT GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class ContactGenerator(BaseComponentGenerator):
    component_type = ComponentType.CONTACT

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "Contact Us")
        desc = spec.props.get("description", "We'd love to hear from you.")
        email = spec.props.get("email", "hello@example.com")
        return f"""<section class="py-24 px-6" style="background:{theme.colors.background};color:{theme.colors.text_primary}">
  <div class="max-w-4xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold text-center mb-4">{title}</h2>
    <p class="text-center mb-12" style="color:{theme.colors.text_secondary}">{desc}</p>
    <div class="max-w-lg mx-auto space-y-4">
      <input type="text" placeholder="Name" class="w-full px-4 py-3 rounded-xl border text-sm outline-none focus:ring-2" style="background:{theme.colors.surface};border-color:{theme.colors.border};color:{theme.colors.text_primary};--tw-ring-color:{theme.colors.primary}">
      <input type="email" placeholder="Email" class="w-full px-4 py-3 rounded-xl border text-sm outline-none focus:ring-2" style="background:{theme.colors.surface};border-color:{theme.colors.border};color:{theme.colors.text_primary};--tw-ring-color:{theme.colors.primary}">
      <textarea rows="4" placeholder="Message" class="w-full px-4 py-3 rounded-xl border text-sm outline-none focus:ring-2 resize-none" style="background:{theme.colors.surface};border-color:{theme.colors.border};color:{theme.colors.text_primary};--tw-ring-color:{theme.colors.primary}"></textarea>
      <button class="w-full py-3 rounded-xl text-sm font-semibold text-white transition-transform hover:scale-[1.02]" style="background:{theme.colors.primary}">Send Message</button>
    </div>
    <p class="text-center mt-8 text-sm" style="color:{theme.colors.text_secondary}">Or email us at <a href="mailto:{email}" style="color:{theme.colors.primary}">{email}</a></p>
  </div>
</section>"""


# ══════════════════════════════════════════════════════════════════════════════
# REMAINING GENERATORS (Gallery, Team, Stats, Menu, Reservation, Projects,
#                       Skills, BlogPosts, Newsletter, Services, HowItWorks, Logos)
# ══════════════════════════════════════════════════════════════════════════════

class GalleryGenerator(BaseComponentGenerator):
    component_type = ComponentType.GALLERY

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "Gallery")
        count = spec.props.get("items_count", 6)
        items = "".join(
            f'<div class="aspect-video rounded-xl border overflow-hidden" style="background:{theme.colors.surface};border-color:{theme.colors.border}"><div class="w-full h-full flex items-center justify-center text-2xl opacity-30">📷</div></div>'
            for _ in range(count)
        )
        return f"""<section class="py-24 px-6" style="background:{theme.colors.background};color:{theme.colors.text_primary}">
  <div class="max-w-7xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold text-center mb-16">{title}</h2>
    <div class="grid md:grid-cols-3 gap-4">{items}</div>
  </div>
</section>"""


class TeamGenerator(BaseComponentGenerator):
    component_type = ComponentType.TEAM

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "Our Team")
        members = spec.props.get("members", [
            {"name": "Alex Rivera", "role": "CEO"},
            {"name": "Jordan Lee", "role": "CTO"},
            {"name": "Sam Patel", "role": "Design Lead"},
        ])
        cards = ""
        for m in members:
            cards += f"""<div class="text-center">
      <div class="w-24 h-24 mx-auto rounded-full mb-4 flex items-center justify-center text-2xl font-bold" style="background:{theme.colors.primary}22;color:{theme.colors.primary}">{m['name'][0]}</div>
      <h3 class="font-semibold">{m['name']}</h3>
      <p class="text-sm" style="color:{theme.colors.text_secondary}">{m['role']}</p>
    </div>"""
        return f"""<section class="py-24 px-6" style="background:{theme.colors.surface};color:{theme.colors.text_primary}">
  <div class="max-w-7xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold text-center mb-16">{title}</h2>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-8">{cards}</div>
  </div>
</section>"""


class StatsGenerator(BaseComponentGenerator):
    component_type = ComponentType.STATS

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "By the Numbers")
        stats = spec.props.get("stats", [
            {"value": "10K+", "label": "Customers"},
            {"value": "99.9%", "label": "Uptime"},
            {"value": "50M+", "label": "Requests"},
            {"value": "4.9★", "label": "Rating"},
        ])
        items = ""
        for s in stats:
            items += f"""<div class="text-center">
      <div class="text-4xl font-black mb-2" style="color:{theme.colors.primary}">{s['value']}</div>
      <p class="text-sm" style="color:{theme.colors.text_secondary}">{s['label']}</p>
    </div>"""
        return f"""<section class="py-24 px-6" style="background:{theme.colors.surface};color:{theme.colors.text_primary}">
  <div class="max-w-5xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold text-center mb-16">{title}</h2>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-8">{items}</div>
  </div>
</section>"""


class MenuGenerator(BaseComponentGenerator):
    component_type = ComponentType.MENU

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "Our Menu")
        categories = spec.props.get("categories", [
            {"name": "Starters", "items": [{"name": "Bruschetta", "price": "$12"}]},
            {"name": "Mains", "items": [{"name": "Grilled Salmon", "price": "$28"}]},
        ])
        sections = ""
        for cat in categories:
            items_html = "".join(
                f'<div class="flex justify-between items-center py-3 border-b" style="border-color:{theme.colors.border}"><span>{item["name"]}</span><span style="color:{theme.colors.primary}">{item["price"]}</span></div>'
                for item in cat.get("items", [])
            )
            sections += f'<div class="mb-8"><h3 class="text-xl font-semibold mb-4" style="color:{theme.colors.primary}">{cat["name"]}</h3>{items_html}</div>'
        return f"""<section class="py-24 px-6" style="background:{theme.colors.background};color:{theme.colors.text_primary}">
  <div class="max-w-3xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold text-center mb-16">{title}</h2>
    {sections}
  </div>
</section>"""


class ReservationGenerator(BaseComponentGenerator):
    component_type = ComponentType.RESERVATION

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "Reserve a Table")
        return f"""<section class="py-24 px-6" style="background:{theme.colors.surface};color:{theme.colors.text_primary}">
  <div class="max-w-lg mx-auto text-center">
    <h2 class="text-3xl font-bold mb-4">{title}</h2>
    <p class="mb-8" style="color:{theme.colors.text_secondary}">Book your dining experience with us.</p>
    <div class="space-y-4 text-left">
      <input type="date" class="w-full px-4 py-3 rounded-xl border text-sm" style="background:{theme.colors.background};border-color:{theme.colors.border};color:{theme.colors.text_primary}">
      <input type="time" class="w-full px-4 py-3 rounded-xl border text-sm" style="background:{theme.colors.background};border-color:{theme.colors.border};color:{theme.colors.text_primary}">
      <input type="number" placeholder="Guests" min="1" class="w-full px-4 py-3 rounded-xl border text-sm" style="background:{theme.colors.background};border-color:{theme.colors.border};color:{theme.colors.text_primary}">
      <button class="w-full py-3 rounded-xl font-semibold text-white" style="background:{theme.colors.primary}">Reserve Now</button>
    </div>
  </div>
</section>"""


class ProjectsGenerator(BaseComponentGenerator):
    component_type = ComponentType.PROJECTS

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "Projects")
        projects = spec.props.get("projects", [
            {"name": "Project Alpha", "description": "A complete redesign.", "tags": ["Design"]},
            {"name": "Project Beta", "description": "Mobile-first experience.", "tags": ["Mobile"]},
            {"name": "Project Gamma", "description": "Enterprise dashboard.", "tags": ["Analytics"]},
        ])
        cards = ""
        for p in projects:
            tags = "".join(f'<span class="px-2 py-1 rounded-md text-xs" style="background:{theme.colors.primary}15;color:{theme.colors.primary}">{t}</span>' for t in p.get("tags", []))
            cards += f"""<div class="rounded-2xl border p-6 backdrop-blur transition-all hover:scale-[1.02]" style="background:rgba(255,255,255,0.03);border-color:{theme.colors.border}">
      <h3 class="text-lg font-semibold mb-2">{p['name']}</h3>
      <p class="text-sm mb-4" style="color:{theme.colors.text_secondary}">{p['description']}</p>
      <div class="flex flex-wrap gap-2">{tags}</div>
    </div>"""
        return f"""<section class="py-24 px-6" style="background:{theme.colors.background};color:{theme.colors.text_primary}">
  <div class="max-w-7xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold text-center mb-16">{title}</h2>
    <div class="grid md:grid-cols-3 gap-6">{cards}</div>
  </div>
</section>"""


class SkillsGenerator(BaseComponentGenerator):
    component_type = ComponentType.SKILLS

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "Skills")
        skills = spec.props.get("skills", ["Python", "JavaScript", "React", "Docker"])
        pills = "".join(
            f'<span class="px-4 py-2 rounded-full text-sm font-medium border" style="border-color:{theme.colors.primary}33;color:{theme.colors.primary};background:{theme.colors.primary}10">{s}</span>'
            for s in skills
        )
        return f"""<section class="py-24 px-6" style="background:{theme.colors.surface};color:{theme.colors.text_primary}">
  <div class="max-w-4xl mx-auto text-center">
    <h2 class="text-3xl md:text-4xl font-bold mb-12">{title}</h2>
    <div class="flex flex-wrap justify-center gap-3">{pills}</div>
  </div>
</section>"""


class BlogPostsGenerator(BaseComponentGenerator):
    component_type = ComponentType.BLOG_POSTS

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "Blog")
        posts = spec.props.get("posts", [
            {"title": "Getting Started", "excerpt": "Everything you need to know.", "date": "Jan 2025"},
            {"title": "Best Practices", "excerpt": "Tips from our team.", "date": "Feb 2025"},
            {"title": "Roadmap 2025", "excerpt": "What's next.", "date": "Mar 2025"},
        ])
        cards = ""
        for p in posts:
            cards += f"""<div class="rounded-2xl border p-6" style="background:rgba(255,255,255,0.03);border-color:{theme.colors.border}">
      <span class="text-xs" style="color:{theme.colors.text_secondary}">{p.get('date', '')}</span>
      <h3 class="text-lg font-semibold mt-2 mb-2">{p['title']}</h3>
      <p class="text-sm" style="color:{theme.colors.text_secondary}">{p['excerpt']}</p>
      <a href="#" class="text-sm mt-4 inline-block" style="color:{theme.colors.primary}">Read more →</a>
    </div>"""
        return f"""<section class="py-24 px-6" style="background:{theme.colors.background};color:{theme.colors.text_primary}">
  <div class="max-w-7xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold text-center mb-16">{title}</h2>
    <div class="grid md:grid-cols-3 gap-6">{cards}</div>
  </div>
</section>"""


class NewsletterGenerator(BaseComponentGenerator):
    component_type = ComponentType.NEWSLETTER

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "Stay Updated")
        desc = spec.props.get("description", "Get the latest news delivered to your inbox.")
        btn = spec.props.get("button_text", "Subscribe")
        return f"""<section class="py-24 px-6" style="background:{theme.colors.surface};color:{theme.colors.text_primary}">
  <div class="max-w-xl mx-auto text-center">
    <h2 class="text-3xl font-bold mb-4">{title}</h2>
    <p class="mb-8" style="color:{theme.colors.text_secondary}">{desc}</p>
    <div class="flex gap-3">
      <input type="email" placeholder="Enter your email" class="flex-1 px-4 py-3 rounded-xl border text-sm outline-none" style="background:{theme.colors.background};border-color:{theme.colors.border};color:{theme.colors.text_primary}">
      <button class="px-6 py-3 rounded-xl text-sm font-semibold text-white" style="background:{theme.colors.primary}">{btn}</button>
    </div>
  </div>
</section>"""


class ServicesGenerator(BaseComponentGenerator):
    component_type = ComponentType.SERVICES

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "Our Services")
        services = spec.props.get("services", [
            {"name": "Web Development", "description": "Custom websites."},
            {"name": "Mobile Apps", "description": "iOS and Android."},
            {"name": "Cloud", "description": "Scalable infrastructure."},
        ])
        icons = ["🌐", "📱", "☁️", "🎨", "📊", "🔧"]
        cards = ""
        for i, s in enumerate(services):
            cards += f"""<div class="rounded-2xl border p-6" style="background:rgba(255,255,255,0.03);border-color:{theme.colors.border}">
      <div class="text-3xl mb-4">{icons[i % len(icons)]}</div>
      <h3 class="text-lg font-semibold mb-2">{s['name']}</h3>
      <p class="text-sm" style="color:{theme.colors.text_secondary}">{s['description']}</p>
    </div>"""
        return f"""<section class="py-24 px-6" style="background:{theme.colors.background};color:{theme.colors.text_primary}">
  <div class="max-w-7xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold text-center mb-16">{title}</h2>
    <div class="grid md:grid-cols-3 gap-6">{cards}</div>
  </div>
</section>"""


class HowItWorksGenerator(BaseComponentGenerator):
    component_type = ComponentType.HOW_IT_WORKS

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "How It Works")
        steps = spec.props.get("steps", [
            {"step": "1", "title": "Sign Up", "description": "Create your account."},
            {"step": "2", "title": "Configure", "description": "Set up your workspace."},
            {"step": "3", "title": "Launch", "description": "Go live."},
        ])
        items = ""
        for s in steps:
            items += f"""<div class="text-center">
      <div class="w-14 h-14 mx-auto rounded-full flex items-center justify-center text-xl font-bold mb-4" style="background:{theme.colors.primary}20;color:{theme.colors.primary}">{s['step']}</div>
      <h3 class="text-lg font-semibold mb-2">{s['title']}</h3>
      <p class="text-sm" style="color:{theme.colors.text_secondary}">{s['description']}</p>
    </div>"""
        return f"""<section class="py-24 px-6" style="background:{theme.colors.surface};color:{theme.colors.text_primary}">
  <div class="max-w-5xl mx-auto">
    <h2 class="text-3xl md:text-4xl font-bold text-center mb-16">{title}</h2>
    <div class="grid md:grid-cols-3 gap-12">{items}</div>
  </div>
</section>"""


class LogosGenerator(BaseComponentGenerator):
    component_type = ComponentType.LOGOS

    async def generate(self, spec, theme, provider, config) -> str:
        prompt = self.build_prompt(spec, theme)
        try:
            raw = await self._call_llm(prompt, provider, config)
            return _clean_html(raw)
        except Exception:
            return self._fallback_html(spec, theme)

    def _fallback_html(self, spec, theme) -> str:
        title = spec.props.get("title", "Trusted By")
        logos = spec.props.get("logos", ["TechCorp", "InnovateLabs", "DataStream", "CloudFirst", "NextGen"])
        items = "".join(
            f'<div class="text-lg font-bold opacity-40 hover:opacity-70 transition-opacity">{l}</div>'
            for l in logos
        )
        return f"""<section class="py-16 px-6 border-y" style="background:{theme.colors.background};color:{theme.colors.text_primary};border-color:{theme.colors.border}">
  <div class="max-w-7xl mx-auto">
    <p class="text-center text-sm mb-8 uppercase tracking-widest" style="color:{theme.colors.text_secondary}">{title}</p>
    <div class="flex flex-wrap justify-center items-center gap-12">{items}</div>
  </div>
</section>"""


# ══════════════════════════════════════════════════════════════════════════════
# FACTORY: Register all generators
# ══════════════════════════════════════════════════════════════════════════════

ALL_GENERATORS: list[type[BaseComponentGenerator]] = [
    NavbarGenerator,
    HeroGenerator,
    FeaturesGenerator,
    PricingGenerator,
    FAQGenerator,
    FooterGenerator,
    CTAGenerator,
    TestimonialsGenerator,
    AboutGenerator,
    ContactGenerator,
    GalleryGenerator,
    TeamGenerator,
    StatsGenerator,
    MenuGenerator,
    ReservationGenerator,
    ProjectsGenerator,
    SkillsGenerator,
    BlogPostsGenerator,
    NewsletterGenerator,
    ServicesGenerator,
    HowItWorksGenerator,
    LogosGenerator,
]


def create_default_registry():
    """Create a ComponentRegistry with all default generators registered."""
    from ai.registry.component_registry import ComponentRegistry
    registry = ComponentRegistry()
    for gen_cls in ALL_GENERATORS:
        registry.register(gen_cls())
    return registry
