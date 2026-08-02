"""
tests/unit/test_phase6_design.py — Phase 6: Comprehensive Test Suite

Tests for:
  1. DesignSpec resolution (all 12 style presets)
  2. Asset provider (URL generation, caching, fallback)
  3. SVG asset generation (icons, avatars, logos, patterns)
  4. Interaction library injection
  5. GenerationRequest → pipeline integration
  6. Analyzer + Planner override behavior
"""
from __future__ import annotations

import pytest

from ai.assets.provider import (
    AssetImage,
    CachingAssetProvider,
    LocalAssetProvider,
    UnsplashSourceProvider,
    get_default_asset_provider,
)
from ai.assets.svg_assets import (
    AvatarGenerator,
    LogoGenerator,
    PatternGenerator,
    SVGIcons,
)
from ai.builders.design_resolver import (
    ANIMATION_CLASSES,
    STYLE_TOKENS,
    DesignResolver,
)
from ai.interactions.injector import InteractionInjector
from ai.interactions.library import InteractionLibrary
from ai.planner.analyzer import PromptAnalyzer
from ai.planner.planner import AIPlanner
from schemas.generation import (
    AnimationPreset,
    ComponentPlan,
    ComponentSpec,
    ComponentType,
    ContentTone,
    DesignSpec,
    GenerationRequest,
    ImageCounts,
    PageSpec,
    PromptAnalysisResult,
    StylePreset,
    ThemeMode,
    ToneStyle,
    WebsiteSpec,
    WebsiteType,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DESIGN RESOLVER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDesignResolver:
    def setup_method(self):
        self.resolver = DesignResolver()
        self.spec = WebsiteSpec()

        # Minimal mock theme
        class MockTheme:
            mode = ThemeMode.DARK
            glass_effect = False
        self.theme = MockTheme()

    def test_resolve_default(self):
        design = self.resolver.resolve(self.spec, self.theme)
        assert isinstance(design, DesignSpec)
        assert design.style_preset == StylePreset.MODERN
        assert design.animation_preset == AnimationPreset.SMOOTH

    @pytest.mark.parametrize("preset", list(StylePreset))
    def test_all_style_presets_resolve(self, preset: StylePreset):
        """Every style preset should resolve without error."""
        design = self.resolver.resolve(self.spec, self.theme, style=preset)
        assert design.style_preset == preset
        assert isinstance(design.button_style, str)
        assert len(design.button_style) > 0
        assert isinstance(design.card_style, str)
        assert isinstance(design.border_radius, str)

    @pytest.mark.parametrize("anim", list(AnimationPreset))
    def test_all_animation_presets_resolve(self, anim: AnimationPreset):
        design = self.resolver.resolve(self.spec, self.theme, animation=anim)
        assert design.animation_preset == anim

    def test_glassmorphism_enables_glass(self):
        design = self.resolver.resolve(
            self.spec, self.theme, style=StylePreset.GLASSMORPHISM,
        )
        assert design.glass_effect is True

    def test_luxury_no_gradient(self):
        design = self.resolver.resolve(
            self.spec, self.theme, style=StylePreset.LUXURY,
        )
        assert design.gradient_enabled is False

    def test_custom_section_variants(self):
        variants = {"Hero": "split", "Pricing": "toggle", "FAQ": "accordion"}
        design = self.resolver.resolve(
            self.spec, self.theme,
            section_variants=variants,
        )
        assert design.section_variants == variants

    def test_auto_variant_selection(self):
        design = self.resolver.resolve(
            self.spec, self.theme, style=StylePreset.APPLE,
        )
        assert design.section_variants.get("Hero") == "centered"

    def test_style_tokens_complete(self):
        """All 12 presets have full token sets."""
        required = {"button_style", "card_style", "border_radius", "elevation"}
        for preset in StylePreset:
            tokens = STYLE_TOKENS[preset]
            for key in required:
                assert key in tokens, f"Missing '{key}' in {preset.value}"

    def test_animation_classes_complete(self):
        """All 4 animation presets have full class sets."""
        required = {"reveal", "hover", "transition", "stagger_delay"}
        for preset in AnimationPreset:
            classes = ANIMATION_CLASSES[preset]
            for key in required:
                assert key in classes, f"Missing '{key}' in {preset.value}"

    def test_content_tone_passthrough(self):
        design = self.resolver.resolve(
            self.spec, self.theme, content_tone=ContentTone.LUXURY,
        )
        assert design.content_tone == ContentTone.LUXURY

    def test_get_animation_classes(self):
        classes = self.resolver.get_animation_classes(AnimationPreset.FANCY)
        assert "hover" in classes
        assert "stagger_delay" in classes


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ASSET PROVIDER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnsplashSourceProvider:
    def setup_method(self):
        self.provider = UnsplashSourceProvider()

    def test_get_images_returns_assets(self):
        images = self.provider.get_images("technology", count=3)
        assert len(images) == 3
        assert all(isinstance(img, AssetImage) for img in images)

    def test_images_have_real_urls(self):
        images = self.provider.get_images("business", count=1)
        assert images[0].url.startswith("https://images.unsplash.com")

    def test_deterministic_selection(self):
        """Same query should return same images (deterministic)."""
        a = self.provider.get_images("tech hero", count=2)
        b = self.provider.get_images("tech hero", count=2)
        assert [i.url for i in a] == [i.url for i in b]

    def test_team_avatars(self):
        avatars = self.provider.get_team_avatars(count=4)
        assert len(avatars) == 4
        assert all("portrait" in img.alt.lower() for img in avatars)

    def test_food_category_mapping(self):
        images = self.provider.get_images("restaurant menu", count=1)
        # Should resolve to food category
        assert images[0].url.startswith("https://")

    def test_img_tag_generation(self):
        images = self.provider.get_images("tech", count=1)
        tag = images[0].to_img_tag(extra_classes="rounded-lg")
        assert "<img" in tag
        assert "loading=\"lazy\"" in tag
        assert "rounded-lg" in tag


class TestLocalAssetProvider:
    def test_generates_svg_placeholders(self):
        provider = LocalAssetProvider()
        images = provider.get_images("test", count=3)
        assert len(images) == 3
        assert all(img.url.startswith("data:image/svg+xml") for img in images)

    def test_gradient_colors_vary(self):
        provider = LocalAssetProvider()
        images = provider.get_images("test", count=6)
        urls = [img.url for img in images]
        assert len(set(urls)) == 6  # All different


class TestCachingAssetProvider:
    def test_cache_hit(self):
        inner = UnsplashSourceProvider()
        cached = CachingAssetProvider(inner, max_size=10)

        first = cached.get_images("technology", count=2)
        second = cached.get_images("technology", count=2)
        assert first is second  # Same object from cache

    def test_cache_miss_different_query(self):
        cached = CachingAssetProvider(UnsplashSourceProvider(), max_size=10)
        a = cached.get_images("technology", count=2)
        b = cached.get_images("food", count=2)
        assert a is not b


class TestDefaultAssetProvider:
    def test_factory_returns_caching_provider(self):
        provider = get_default_asset_provider()
        assert isinstance(provider, CachingAssetProvider)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SVG ASSETS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSVGIcons:
    def test_get_known_icon(self):
        svg = SVGIcons.get("star")
        assert "<svg" in svg
        assert "polygon" in svg

    def test_get_unknown_returns_empty(self):
        assert SVGIcons.get("nonexistent_icon_xyz") == ""

    def test_custom_size(self):
        svg = SVGIcons.get("check", size=32)
        assert 'width="32"' in svg
        assert 'height="32"' in svg

    def test_custom_color(self):
        svg = SVGIcons.get("arrow-right", color="#ff0000")
        assert '#ff0000' in svg

    def test_list_icons(self):
        icons = SVGIcons.list_icons()
        assert len(icons) >= 20
        assert "star" in icons
        assert "check" in icons

    def test_feature_icons(self):
        icons = SVGIcons.get_feature_icons(count=6)
        assert len(icons) == 6
        assert all(isinstance(name, str) for name in icons)


class TestAvatarGenerator:
    def test_generate_svg(self):
        svg = AvatarGenerator.generate("John Doe")
        assert "<svg" in svg
        assert "JD" in svg

    def test_single_name(self):
        svg = AvatarGenerator.generate("Alice")
        assert "AL" in svg

    def test_data_uri(self):
        uri = AvatarGenerator.generate_data_uri("Jane Smith")
        assert uri.startswith("data:image/svg+xml,")
        assert "JS" in uri

    def test_deterministic_color(self):
        a = AvatarGenerator.generate("Test User")
        b = AvatarGenerator.generate("Test User")
        assert a == b


class TestLogoGenerator:
    def test_generate_logo(self):
        svg = LogoGenerator.generate("Acme Corp")
        assert "<svg" in svg

    def test_generate_set(self):
        logos = LogoGenerator.generate_set(["Alpha", "Beta", "Gamma"], size=40)
        assert len(logos) == 3
        assert all("<svg" in svg for svg in logos)


class TestPatternGenerator:
    def test_dots_pattern(self):
        svg = PatternGenerator.dots()
        assert "<svg" in svg
        assert "circle" in svg

    def test_grid_pattern(self):
        svg = PatternGenerator.grid()
        assert "<svg" in svg
        assert "path" in svg

    def test_diagonal_pattern(self):
        svg = PatternGenerator.diagonal()
        assert "<svg" in svg

    def test_css_background(self):
        css = PatternGenerator.get_css_background("dots")
        assert css.startswith("url(")


# ═══════════════════════════════════════════════════════════════════════════════
# 4. INTERACTION LIBRARY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestInteractionLibrary:
    def test_get_known_script(self):
        script = InteractionLibrary.get("faq")
        assert script is not None
        assert "addEventListener" in script

    def test_get_unknown_returns_none(self):
        assert InteractionLibrary.get("nonexistent_script") is None

    def test_list_available(self):
        available = InteractionLibrary.list_available()
        assert len(available) >= 10
        assert "navbar" in available
        assert "faq" in available
        assert "pricing" in available

    def test_get_bundle(self):
        bundle = InteractionLibrary.get_bundle(["faq", "navbar"])
        assert "/* faq */" in bundle
        assert "/* navbar */" in bundle

    def test_get_all(self):
        all_scripts = InteractionLibrary.get_all()
        assert len(all_scripts) > 1000  # Substantial

    def test_scripts_are_iife(self):
        """All scripts should be self-contained IIFEs."""
        for name in InteractionLibrary.list_available():
            script = InteractionLibrary.get(name)
            assert script.startswith("(function()"), f"{name} is not an IIFE"

    def test_no_eval(self):
        """No script should use eval()."""
        for name in InteractionLibrary.list_available():
            script = InteractionLibrary.get(name)
            assert "eval(" not in script, f"{name} uses eval()"


class TestInteractionInjector:
    def setup_method(self):
        self.injector = InteractionInjector()

    def _make_spec_with(self, *component_types: ComponentType) -> WebsiteSpec:
        components = [
            ComponentSpec(type=ct, order=i, variant="default")
            for i, ct in enumerate(component_types)
        ]
        return WebsiteSpec(
            pages=[PageSpec(page_id="main", title="Test", route="/", components=components)],
        )

    def test_injects_faq_script(self):
        spec = self._make_spec_with(ComponentType.NAVBAR, ComponentType.FAQ, ComponentType.FOOTER)
        result = self.injector.inject(spec)
        assert "<script>" in result
        assert "faq" in result.lower()

    def test_injects_navbar_and_scroll(self):
        spec = self._make_spec_with(ComponentType.NAVBAR)
        scripts = self.injector.list_injected(spec)
        assert "navbar" in scripts
        assert "scroll" in scripts

    def test_pricing_toggle(self):
        spec = self._make_spec_with(ComponentType.PRICING)
        scripts = self.injector.list_injected(spec)
        assert "pricing" in scripts

    def test_no_animations_when_disabled(self):
        spec = self._make_spec_with(ComponentType.HERO)
        design = DesignSpec(animation_preset=AnimationPreset.NONE)
        scripts = self.injector.list_injected(spec, design)
        assert "reveal" not in scripts

    def test_reveal_enabled_by_default(self):
        spec = self._make_spec_with(ComponentType.HERO)
        scripts = self.injector.list_injected(spec)
        assert "reveal" in scripts

    def test_empty_spec_minimal_injection(self):
        spec = WebsiteSpec()
        result = self.injector.inject(spec)
        # Even with empty spec, reveal should be injected
        assert "reveal" in result or result == ""


# ═══════════════════════════════════════════════════════════════════════════════
# 5. GENERATION REQUEST SCHEMA TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestGenerationRequest:
    def test_minimal_request(self):
        req = GenerationRequest(prompt="Build a landing page")
        assert req.prompt == "Build a landing page"
        assert req.website_type is None
        assert req.style is None

    def test_full_request(self):
        req = GenerationRequest(
            prompt="Create AI Startup",
            website_type=WebsiteType.SAAS,
            theme=ThemeMode.DARK,
            style=StylePreset.LINEAR,
            animations=AnimationPreset.SMOOTH,
            color="purple",
            sections=["Hero", "Features", "Pricing", "FAQ", "Footer"],
            content_tone=ContentTone.PROFESSIONAL,
            brand_name="NovaTech",
        )
        assert req.website_type == WebsiteType.SAAS
        assert req.style == StylePreset.LINEAR
        assert len(req.sections) == 5

    def test_image_counts(self):
        counts = ImageCounts(hero_images=2, gallery_images=8)
        assert counts.hero_images == 2
        assert counts.gallery_images == 8


class TestDesignSpec:
    def test_defaults(self):
        spec = DesignSpec()
        assert spec.style_preset == StylePreset.MODERN
        assert spec.animation_preset == AnimationPreset.SMOOTH
        assert spec.glass_effect is False

    def test_custom_values(self):
        spec = DesignSpec(
            style_preset=StylePreset.CYBERPUNK,
            glass_effect=True,
            border_radius="0",
        )
        assert spec.border_radius == "0"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. ANALYZER + PLANNER OVERRIDE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyzerOverrides:
    def setup_method(self):
        self.analyzer = PromptAnalyzer()

    def test_no_request_backward_compatible(self):
        result = self.analyzer.analyze("Build a SaaS landing page")
        assert result.website_type in (WebsiteType.SAAS, WebsiteType.LANDING)

    def test_website_type_override(self):
        request = GenerationRequest(
            prompt="Build a website",
            website_type=WebsiteType.PORTFOLIO,
        )
        result = self.analyzer.analyze("Build a website", request=request)
        assert result.website_type == WebsiteType.PORTFOLIO

    def test_theme_override(self):
        request = GenerationRequest(
            prompt="Build a website",
            theme=ThemeMode.LIGHT,
        )
        result = self.analyzer.analyze("Build a dark website", request=request)
        # Request override wins over prompt detection
        assert result.theme == ThemeMode.LIGHT

    def test_color_override(self):
        request = GenerationRequest(
            prompt="Build a blue website",
            color="purple",
        )
        result = self.analyzer.analyze("Build a blue website", request=request)
        assert result.color_hint == "purple"

    def test_sections_merge(self):
        request = GenerationRequest(
            prompt="Build a landing page with pricing",
            sections=["Gallery", "Newsletter"],
        )
        result = self.analyzer.analyze("Build a landing page with pricing", request=request)
        assert "Pricing" in result.requested_components
        assert "Gallery" in result.requested_components
        assert "Newsletter" in result.requested_components


class TestPlannerOverrides:
    def setup_method(self):
        self.planner = AIPlanner()

    def test_no_request_backward_compatible(self):
        analysis = PromptAnalysisResult(website_type=WebsiteType.LANDING)
        plan = self.planner.plan(analysis)
        assert plan.total_components > 0

    def test_explicit_sections_override(self):
        analysis = PromptAnalysisResult(website_type=WebsiteType.LANDING)
        request = GenerationRequest(
            prompt="test",
            sections=["Hero", "Features", "Pricing", "Footer"],
        )
        plan = self.planner.plan(analysis, request=request)
        types = [c.type for c in plan.components]
        assert ComponentType.HERO in types
        assert ComponentType.FEATURES in types
        assert ComponentType.PRICING in types
        assert ComponentType.FOOTER in types

    def test_mandatory_navbar_added(self):
        analysis = PromptAnalysisResult(website_type=WebsiteType.LANDING)
        request = GenerationRequest(
            prompt="test",
            sections=["Hero", "Features"],
        )
        plan = self.planner.plan(analysis, request=request)
        types = [c.type for c in plan.components]
        assert ComponentType.NAVBAR in types
        assert ComponentType.FOOTER in types
