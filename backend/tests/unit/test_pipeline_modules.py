"""
tests/unit/test_pipeline_modules.py — Unit tests for Modules 1-9

Tests the full intelligence layer and generation pipeline:
  Module 1: PromptAnalyzer
  Module 2: AIPlanner
  Module 3: SpecBuilder
  Module 4: ThemeEngine
  Module 5: ComponentRegistry
  Module 7: HTMLBuilder
  Module 8: ValidatorChain
  Module 9: RepairEngine
"""
import pytest

from schemas.generation import (
    ColorPalette,
    ComponentPlan,
    ComponentSpec,
    ComponentType,
    GenerationPlan,
    PageSpec,
    PromptAnalysisResult,
    ThemeMode,
    ThemeSpec,
    ToneStyle,
    WebsiteSpec,
    WebsiteType,
)
from ai.planner.analyzer import PromptAnalyzer
from ai.planner.planner import AIPlanner
from ai.planner.spec_builder import SpecBuilder
from ai.builders.theme_engine import ThemeEngine, ResolvedTheme
from ai.builders.html_builder import HTMLBuilder
from ai.registry.component_registry import ComponentRegistry, BaseComponentGenerator
from ai.validators.chain import (
    ValidatorChain,
    HTMLStructureValidator,
    SecurityValidator,
    SEOValidator,
    Severity,
    ValidationReport,
)
from ai.repair.engine import RepairEngine, RegexRepairStrategy


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 1: PromptAnalyzer
# ══════════════════════════════════════════════════════════════════════════════

class TestPromptAnalyzer:
    """Tests for deterministic prompt analysis."""

    def setup_method(self):
        self.analyzer = PromptAnalyzer()

    def test_saas_landing_page_detection(self):
        result = self.analyzer.analyze(
            "Create a SaaS landing page for an AI startup with pricing"
        )
        assert result.website_type in (WebsiteType.SAAS, WebsiteType.LANDING, WebsiteType.STARTUP)
        assert result.industry == "ai"
        assert result.has_pricing is True
        assert "Pricing" in result.requested_components

    def test_portfolio_detection(self):
        result = self.analyzer.analyze(
            "Build a developer portfolio with projects and skills sections"
        )
        assert result.website_type == WebsiteType.PORTFOLIO
        assert "Projects" in result.requested_components
        assert "Skills" in result.requested_components

    def test_restaurant_detection(self):
        result = self.analyzer.analyze(
            "Create a restaurant website with a menu and reservation system"
        )
        assert result.website_type == WebsiteType.RESTAURANT
        assert "Menu" in result.requested_components
        assert "Reservation" in result.requested_components

    def test_dark_theme_detection(self):
        result = self.analyzer.analyze("Build a dark theme landing page")
        assert result.theme == ThemeMode.DARK

    def test_light_theme_detection(self):
        result = self.analyzer.analyze("Build a clean white minimal website")
        assert result.theme == ThemeMode.LIGHT

    def test_brand_name_extraction_quoted(self):
        result = self.analyzer.analyze('Build a website for "TechNova"')
        assert result.brand_name == "TechNova"

    def test_color_hint_detection(self):
        result = self.analyzer.analyze("Create a neon-styled landing page")
        assert result.color_hint == "neon"

    def test_blue_color_detection(self):
        result = self.analyzer.analyze("Build a blue ocean-themed website")
        assert result.color_hint == "blue"

    def test_minimal_tone_detection(self):
        result = self.analyzer.analyze("Create a minimal, simple, bare portfolio")
        assert result.tone == ToneStyle.MINIMAL

    def test_complexity_simple(self):
        result = self.analyzer.analyze("Portfolio site")
        assert result.prompt_complexity == "simple"

    def test_complexity_complex(self):
        result = self.analyzer.analyze(
            "Build a comprehensive SaaS landing page with pricing tables, "
            "testimonials section, FAQ accordion, newsletter signup, team section, "
            "and contact form with dark blue gradient theme"
        )
        assert result.prompt_complexity == "complex"

    def test_default_values(self):
        result = self.analyzer.analyze("xyz abc 123")
        assert result.website_type == WebsiteType.LANDING  # default
        assert result.industry == "general"
        assert result.theme == ThemeMode.DARK
        assert result.tone == ToneStyle.MODERN

    def test_blog_detection(self):
        result = self.analyzer.analyze("Create a blog with articles and newsletter")
        assert result.website_type == WebsiteType.BLOG
        assert result.has_blog is True
        assert "Newsletter" in result.requested_components

    def test_ecommerce_detection(self):
        result = self.analyzer.analyze("Build an e-commerce store with product gallery")
        assert result.website_type == WebsiteType.ECOMMERCE
        assert result.has_gallery is True


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 2: AIPlanner
# ══════════════════════════════════════════════════════════════════════════════

class TestAIPlanner:
    """Tests for rule-based planning."""

    def setup_method(self):
        self.planner = AIPlanner()

    def test_landing_page_blueprint(self):
        analysis = PromptAnalysisResult(website_type=WebsiteType.LANDING)
        plan = self.planner.plan(analysis)
        assert plan.total_components >= 5
        types = [c.type for c in plan.components]
        assert ComponentType.NAVBAR in types
        assert ComponentType.HERO in types
        assert ComponentType.FOOTER in types

    def test_restaurant_blueprint(self):
        analysis = PromptAnalysisResult(website_type=WebsiteType.RESTAURANT)
        plan = self.planner.plan(analysis)
        types = [c.type for c in plan.components]
        assert ComponentType.MENU in types
        assert ComponentType.RESERVATION in types
        assert ComponentType.GALLERY in types

    def test_user_requested_components_merged(self):
        analysis = PromptAnalysisResult(
            website_type=WebsiteType.LANDING,
            requested_components=["Pricing", "FAQ", "Testimonials"],
        )
        plan = self.planner.plan(analysis)
        types = [c.type for c in plan.components]
        assert ComponentType.PRICING in types
        assert ComponentType.FAQ in types
        assert ComponentType.TESTIMONIALS in types

    def test_mandatory_navbar_footer(self):
        analysis = PromptAnalysisResult(website_type=WebsiteType.UNKNOWN)
        plan = self.planner.plan(analysis)
        types = [c.type for c in plan.components]
        assert types[0] == ComponentType.NAVBAR
        assert types[-1] == ComponentType.FOOTER

    def test_component_ordering(self):
        analysis = PromptAnalysisResult(website_type=WebsiteType.SAAS)
        plan = self.planner.plan(analysis)
        for i, comp in enumerate(plan.components):
            assert comp.order == i

    def test_token_estimation(self):
        analysis = PromptAnalysisResult(website_type=WebsiteType.LANDING)
        plan = self.planner.plan(analysis)
        assert plan.estimated_tokens > 0
        assert plan.estimated_tokens == sum(
            c_tokens
            for c in plan.components
            for c_tokens in [__import__('ai.planner.planner', fromlist=['TOKENS_PER_COMPONENT']).TOKENS_PER_COMPONENT.get(c.type, 400)]
        )


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 3: SpecBuilder
# ══════════════════════════════════════════════════════════════════════════════

class TestSpecBuilder:
    """Tests for WebsiteSpec construction."""

    def setup_method(self):
        self.builder = SpecBuilder()

    def test_builds_valid_spec(self):
        analysis = PromptAnalysisResult(
            website_type=WebsiteType.SAAS,
            industry="ai",
            brand_name="TechNova",
        )
        plan = GenerationPlan(
            website_type=WebsiteType.SAAS,
            industry="ai",
            components=[
                ComponentPlan(type=ComponentType.NAVBAR, order=0),
                ComponentPlan(type=ComponentType.HERO, order=1),
                ComponentPlan(type=ComponentType.FOOTER, order=2),
            ],
            total_components=3,
        )
        spec = self.builder.build(analysis, plan)

        assert spec.site_name == "TechNova"
        assert spec.industry == "ai"
        assert spec.website_type == WebsiteType.SAAS
        assert len(spec.pages) == 1
        assert len(spec.all_components) == 3
        assert spec.pipeline_version == "V1"

    def test_default_props_populated(self):
        analysis = PromptAnalysisResult(brand_name="TestBrand")
        plan = GenerationPlan(
            website_type=WebsiteType.LANDING,
            industry="general",
            components=[ComponentPlan(type=ComponentType.HERO, order=0)],
            total_components=1,
        )
        spec = self.builder.build(analysis, plan)
        hero = spec.all_components[0]
        assert "headline" in hero.props
        assert "TestBrand" in hero.props["headline"]

    def test_meta_description(self):
        analysis = PromptAnalysisResult(
            website_type=WebsiteType.PORTFOLIO,
            industry="technology",
            brand_name="DevStudio",
        )
        plan = GenerationPlan(
            website_type=WebsiteType.PORTFOLIO,
            industry="technology",
            components=[],
            total_components=0,
        )
        spec = self.builder.build(analysis, plan)
        assert "DevStudio" in spec.meta_description
        assert "portfolio" in spec.meta_description


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 4: ThemeEngine
# ══════════════════════════════════════════════════════════════════════════════

class TestThemeEngine:
    """Tests for theme resolution."""

    def setup_method(self):
        self.engine = ThemeEngine()

    def test_dark_mode_default(self):
        theme_spec = ThemeSpec(mode=ThemeMode.DARK)
        analysis = PromptAnalysisResult()
        resolved = self.engine.resolve(theme_spec, analysis)
        assert resolved.mode == ThemeMode.DARK
        assert resolved.colors.background == "#020617"

    def test_light_mode(self):
        theme_spec = ThemeSpec(mode=ThemeMode.LIGHT)
        analysis = PromptAnalysisResult()
        resolved = self.engine.resolve(theme_spec, analysis)
        assert resolved.mode == ThemeMode.LIGHT
        assert resolved.colors.background == "#ffffff"

    def test_color_hint_neon(self):
        theme_spec = ThemeSpec(mode=ThemeMode.DARK)
        analysis = PromptAnalysisResult(color_hint="neon")
        resolved = self.engine.resolve(theme_spec, analysis)
        assert resolved.colors.primary == "#00ff88"

    def test_color_hint_purple(self):
        theme_spec = ThemeSpec(mode=ThemeMode.DARK)
        analysis = PromptAnalysisResult(color_hint="purple")
        resolved = self.engine.resolve(theme_spec, analysis)
        assert resolved.colors.primary == "#8b5cf6"

    def test_css_variables(self):
        theme_spec = ThemeSpec()
        analysis = PromptAnalysisResult()
        resolved = self.engine.resolve(theme_spec, analysis)
        css = resolved.css_variables
        assert "--color-primary" in css
        assert "--color-bg" in css
        assert "--font-heading" in css

    def test_font_imports(self):
        theme_spec = ThemeSpec()
        analysis = PromptAnalysisResult()
        resolved = self.engine.resolve(theme_spec, analysis)
        imports = resolved.font_imports
        assert "fonts.googleapis.com" in imports
        assert "Inter" in imports

    def test_techy_tone_uses_jetbrains(self):
        theme_spec = ThemeSpec(tone=ToneStyle.TECHY)
        analysis = PromptAnalysisResult()
        resolved = self.engine.resolve(theme_spec, analysis)
        assert "JetBrains" in resolved.heading_font

    def test_elegant_tone_uses_playfair(self):
        theme_spec = ThemeSpec(tone=ToneStyle.ELEGANT)
        analysis = PromptAnalysisResult()
        resolved = self.engine.resolve(theme_spec, analysis)
        assert "Playfair" in resolved.heading_font


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 5: ComponentRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestComponentRegistry:
    """Tests for the registry pattern."""

    def test_register_and_get(self):
        registry = ComponentRegistry()
        # Use a mock generator
        class MockGen(BaseComponentGenerator):
            component_type = ComponentType.HERO
            async def generate(self, spec, theme, provider, config):
                return "<section>Hero</section>"
        gen = MockGen()
        registry.register(gen)
        assert registry.has(ComponentType.HERO)
        assert registry.get(ComponentType.HERO) is gen

    def test_unregistered_returns_none(self):
        registry = ComponentRegistry()
        assert registry.get(ComponentType.PRICING) is None
        assert not registry.has(ComponentType.PRICING)

    def test_default_registry_has_all_generators(self):
        from ai.registry.generators.all_generators import create_default_registry
        registry = create_default_registry()
        assert registry.count >= 20
        # Check key types
        assert registry.has(ComponentType.NAVBAR)
        assert registry.has(ComponentType.HERO)
        assert registry.has(ComponentType.FEATURES)
        assert registry.has(ComponentType.PRICING)
        assert registry.has(ComponentType.FAQ)
        assert registry.has(ComponentType.FOOTER)
        assert registry.has(ComponentType.TESTIMONIALS)
        assert registry.has(ComponentType.CONTACT)

    def test_registered_types_list(self):
        registry = ComponentRegistry()
        class MockGen(BaseComponentGenerator):
            component_type = ComponentType.FAQ
            async def generate(self, spec, theme, provider, config):
                return ""
        registry.register(MockGen())
        assert ComponentType.FAQ in registry.registered_types


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 7: HTMLBuilder
# ══════════════════════════════════════════════════════════════════════════════

class TestHTMLBuilder:
    """Tests for HTML assembly."""

    def setup_method(self):
        self.builder = HTMLBuilder()

    def test_builds_complete_html(self):
        spec = WebsiteSpec(
            site_name="TestSite",
            pages=[PageSpec(
                components=[
                    ComponentSpec(type=ComponentType.NAVBAR, order=0),
                    ComponentSpec(type=ComponentType.HERO, order=1),
                ]
            )],
        )
        theme = ResolvedTheme(
            colors=ColorPalette(),
            mode=ThemeMode.DARK,
            tone=ToneStyle.MODERN,
        )
        component_html = {
            0: "<nav>Navbar</nav>",
            1: "<section>Hero</section>",
        }
        result = self.builder.build(spec, theme, component_html)
        assert "<!DOCTYPE html>" in result
        assert "<nav>Navbar</nav>" in result
        assert "<section>Hero</section>" in result
        assert "TestSite" in result

    def test_body_only_mode(self):
        spec = WebsiteSpec(pages=[PageSpec(
            components=[ComponentSpec(type=ComponentType.HERO, order=0)]
        )])
        theme = ResolvedTheme(
            colors=ColorPalette(), mode=ThemeMode.DARK, tone=ToneStyle.MODERN,
        )
        body = self.builder.build_body_only(spec, theme, {0: "<section>Hero</section>"})
        assert "<!DOCTYPE" not in body
        assert "<section>Hero</section>" in body

    def test_empty_spec_fallback(self):
        spec = WebsiteSpec(site_name="Empty")
        theme = ResolvedTheme(
            colors=ColorPalette(), mode=ThemeMode.DARK, tone=ToneStyle.MODERN,
        )
        result = self.builder.build(spec, theme, {})
        assert "<!DOCTYPE html>" in result
        assert "Empty" in result

    def test_css_variables_injected(self):
        spec = WebsiteSpec(pages=[PageSpec()])
        theme = ResolvedTheme(
            colors=ColorPalette(), mode=ThemeMode.DARK, tone=ToneStyle.MODERN,
        )
        result = self.builder.build(spec, theme, {})
        assert "--color-primary" in result
        assert "--color-bg" in result

    def test_component_ordering(self):
        spec = WebsiteSpec(pages=[PageSpec(
            components=[
                ComponentSpec(type=ComponentType.FOOTER, order=2),
                ComponentSpec(type=ComponentType.HERO, order=1),
                ComponentSpec(type=ComponentType.NAVBAR, order=0),
            ]
        )])
        theme = ResolvedTheme(
            colors=ColorPalette(), mode=ThemeMode.DARK, tone=ToneStyle.MODERN,
        )
        component_html = {
            0: "<nav>Nav</nav>",
            1: "<section>Hero</section>",
            2: "<footer>Foot</footer>",
        }
        result = self.builder.build(spec, theme, component_html)
        nav_pos = result.index("Nav")
        hero_pos = result.index("Hero")
        foot_pos = result.index("Foot")
        assert nav_pos < hero_pos < foot_pos


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 8: ValidatorChain
# ══════════════════════════════════════════════════════════════════════════════

class TestValidatorChain:
    """Tests for HTML validation."""

    def test_valid_html_passes(self):
        chain = ValidatorChain.default()
        html = """<section class="py-20">
            <h1>Hello World</h1>
            <p>Some content here</p>
        </section>"""
        report = chain.validate(html)
        assert report.is_valid

    def test_code_fences_detected(self):
        validator = HTMLStructureValidator()
        html = '```html\n<section>Test</section>\n```'
        issues = validator.validate(html)
        assert any(i.fix_hint == "strip_code_fences" for i in issues)

    def test_think_blocks_detected(self):
        validator = HTMLStructureValidator()
        html = '<think>reasoning</think><section>Test</section>'
        issues = validator.validate(html)
        assert any(i.fix_hint == "strip_think_blocks" for i in issues)

    def test_script_tag_detected(self):
        validator = SecurityValidator()
        html = '<section>Test</section><script>alert("xss")</script>'
        issues = validator.validate(html)
        assert len(issues) > 0
        assert any(i.severity == Severity.ERROR for i in issues)

    def test_javascript_url_detected(self):
        validator = SecurityValidator()
        html = '<a href="javascript:alert(1)">Click</a>'
        issues = validator.validate(html)
        assert len(issues) > 0

    def test_seo_no_h1_warning(self):
        validator = SEOValidator()
        html = '<section><h2>Title</h2><p>Content</p></section>'
        issues = validator.validate(html)
        assert any("h1" in i.message.lower() for i in issues)

    def test_seo_multiple_h1_warning(self):
        validator = SEOValidator()
        html = '<h1>First</h1><h1>Second</h1>'
        issues = validator.validate(html)
        assert any("Multiple" in i.message for i in issues)

    def test_empty_html_error(self):
        validator = HTMLStructureValidator()
        issues = validator.validate("")
        assert any(i.severity == Severity.ERROR for i in issues)

    def test_score_calculation(self):
        report = ValidationReport()
        assert report.score == 100.0
        assert report.is_valid

    def test_score_with_errors(self):
        from ai.validators.chain import ValidationIssue
        report = ValidationReport(issues=[
            ValidationIssue("test", Severity.ERROR, "error1"),
            ValidationIssue("test", Severity.WARNING, "warn1"),
        ])
        assert report.score == 75.0  # 100 - 20 - 5
        assert not report.is_valid


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 9: RepairEngine
# ══════════════════════════════════════════════════════════════════════════════

class TestRepairEngine:
    """Tests for the repair loop."""

    def test_strips_code_fences(self):
        strategy = RegexRepairStrategy()
        from ai.validators.chain import ValidationIssue
        html = '```html\n<section>Test</section>\n```'
        issues = [ValidationIssue("test", Severity.ERROR, "fences", "strip_code_fences")]
        result = strategy.repair(html, issues)
        assert "```" not in result
        assert "<section>Test</section>" in result

    def test_strips_think_blocks(self):
        strategy = RegexRepairStrategy()
        from ai.validators.chain import ValidationIssue
        html = '<think>reasoning here</think><section>Content</section>'
        issues = [ValidationIssue("test", Severity.ERROR, "think", "strip_think_blocks")]
        result = strategy.repair(html, issues)
        assert "<think>" not in result
        assert "<section>Content</section>" in result

    def test_strips_script_tags(self):
        strategy = RegexRepairStrategy()
        from ai.validators.chain import ValidationIssue
        html = '<section>Good</section><script>alert("bad")</script>'
        issues = [ValidationIssue("test", Severity.ERROR, "script", "strip_dangerous_content")]
        result = strategy.repair(html, issues)
        assert "<script>" not in result
        assert "<section>Good</section>" in result

    def test_strips_event_handlers(self):
        strategy = RegexRepairStrategy()
        from ai.validators.chain import ValidationIssue
        html = '<button onclick="alert(1)">Click</button>'
        issues = [ValidationIssue("test", Severity.ERROR, "handler", "strip_dangerous_content")]
        result = strategy.repair(html, issues)
        assert "onclick" not in result
        assert "<button" in result

    def test_closes_unclosed_tags(self):
        strategy = RegexRepairStrategy()
        from ai.validators.chain import ValidationIssue
        html = '<section><div>Content'
        issues = [ValidationIssue("test", Severity.ERROR, "unclosed", "close_unclosed_tags")]
        result = strategy.repair(html, issues)
        assert result.count("</section>") == 1
        assert result.count("</div>") == 1

    def test_adds_alt_attributes(self):
        strategy = RegexRepairStrategy()
        from ai.validators.chain import ValidationIssue
        html = '<img src="test.jpg">'
        issues = [ValidationIssue("test", Severity.WARNING, "alt", "add_alt_attribute")]
        result = strategy.repair(html, issues)
        assert 'alt=""' in result

    def test_full_repair_loop(self):
        engine = RepairEngine(max_retries=3)
        chain = ValidatorChain.default()
        html = '```html\n<section><h1>Title</h1><script>bad()</script></section>\n```'
        repaired, report = engine.repair(html, chain)
        assert "```" not in repaired
        assert "<script>" not in repaired

    def test_valid_html_passes_through(self):
        engine = RepairEngine()
        chain = ValidatorChain.default()
        html = '<section><h1>Hello</h1><p>World</p></section>'
        repaired, report = engine.repair(html, chain)
        assert repaired == html
        assert report.is_valid


# ══════════════════════════════════════════════════════════════════════════════
# END-TO-END: Schema Integration
# ══════════════════════════════════════════════════════════════════════════════

class TestSchemaIntegration:
    """Tests for schema integration across modules."""

    def test_full_analysis_to_spec_flow(self):
        """Module 1 → 2 → 3 end-to-end."""
        analyzer = PromptAnalyzer()
        planner = AIPlanner()
        builder = SpecBuilder()

        analysis = analyzer.analyze(
            "Create a SaaS landing page for an AI startup called TechNova with pricing and FAQ"
        )
        plan = planner.plan(analysis)
        spec = builder.build(analysis, plan)

        assert spec.site_name == "TechNova"
        assert spec.website_type in (WebsiteType.SAAS, WebsiteType.LANDING, WebsiteType.STARTUP)
        assert spec.industry == "ai"
        assert len(spec.all_components) > 0
        assert any(c.type == ComponentType.PRICING for c in spec.all_components)
        assert any(c.type == ComponentType.FAQ for c in spec.all_components)

    def test_spec_to_theme_flow(self):
        """Module 3 → 4 integration."""
        spec = WebsiteSpec(
            theme=ThemeSpec(mode=ThemeMode.DARK, tone=ToneStyle.TECHY),
        )
        analysis = PromptAnalysisResult(color_hint="neon")
        engine = ThemeEngine()
        theme = engine.resolve(spec.theme, analysis)

        assert theme.colors.primary == "#00ff88"
        assert "JetBrains" in theme.heading_font
        assert theme.glass_effect is True
