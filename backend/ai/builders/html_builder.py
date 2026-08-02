"""
ai/builders/html_builder.py — Module 7: HTMLBuilder

Assembles individual component HTML fragments into a complete, valid page.

Responsibilities:
  1. Generate the page wrapper (DOCTYPE, head, meta, fonts, CSS variables)
  2. Inject theme CSS custom properties
  3. Assemble components in order
  4. Produce export-ready HTML

Input: list of (ComponentSpec, html_string) tuples + ResolvedTheme
Output: Complete HTML document string
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from schemas.generation import ComponentSpec, WebsiteSpec

if TYPE_CHECKING:
    from ai.builders.theme_engine import ResolvedTheme

logger = logging.getLogger("ai-site-gen")


class HTMLBuilder:
    """
    Module 7: Assembles component HTML into a complete page.

    Usage:
        builder = HTMLBuilder()
        html = builder.build(spec, theme, component_html_map)
    """

    def build(
        self,
        spec: WebsiteSpec,
        theme: "ResolvedTheme",
        component_html: dict[int, str],
    ) -> str:
        """
        Build a complete HTML page from component fragments.

        Args:
            spec: WebsiteSpec with page structure
            theme: ResolvedTheme with CSS variables and font imports
            component_html: Map of component order → rendered HTML string

        Returns:
            Complete HTML document string
        """
        # Get all components from the first page (single page for V1)
        page = spec.pages[0] if spec.pages else None
        if not page:
            logger.warning("No pages in WebsiteSpec; returning empty page")
            return self._empty_page(spec, theme)

        # Assemble components in order
        body_parts: list[str] = []
        for component in sorted(page.components, key=lambda c: c.order):
            html = component_html.get(component.order, "")
            if html:
                body_parts.append(f"  <!-- {component.type.value} -->\n  {html}")
            else:
                logger.warning(
                    f"Missing HTML for component {component.type.value} "
                    f"(order={component.order})"
                )

        body_content = "\n\n".join(body_parts)

        return self._wrap_page(spec, theme, body_content)

    def build_body_only(
        self,
        spec: WebsiteSpec,
        theme: "ResolvedTheme",
        component_html: dict[int, str],
    ) -> str:
        """
        Build only the body content (for streaming into existing preview frames).

        Returns HTML body content without DOCTYPE/head/body wrappers.
        """
        page = spec.pages[0] if spec.pages else None
        if not page:
            return ""

        parts: list[str] = []
        for component in sorted(page.components, key=lambda c: c.order):
            html = component_html.get(component.order, "")
            if html:
                parts.append(html)

        return "\n\n".join(parts)

    def _wrap_page(
        self,
        spec: WebsiteSpec,
        theme: "ResolvedTheme",
        body_content: str,
    ) -> str:
        """Wrap body content in a complete HTML document."""
        font_imports = theme.font_imports
        css_vars = theme.css_variables

        # Base styles for dark/light modes
        base_styles = f"""
    html, body {{
      margin: 0;
      padding: 0;
      min-height: 100%;
      font-family: var(--font-body);
      background: var(--color-bg);
      color: var(--color-text);
      scroll-behavior: smooth;
      -webkit-font-smoothing: antialiased;
    }}
    h1, h2, h3, h4, h5, h6 {{
      font-family: var(--font-heading);
    }}
    * {{
      box-sizing: border-box;
    }}"""

        # Glass morphism utility class
        glass_style = """
    .glass {{
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid var(--color-border);
    }}"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{spec.meta_description}">
  <title>{spec.site_name}</title>
  {font_imports}
  <link rel="stylesheet" href="./preview-tailwind.css">
  <style>
    {css_vars}
    {base_styles}
    {glass_style if theme.glass_effect else ""}
  </style>
</head>
<body>
{body_content}
</body>
</html>"""

    def _empty_page(self, spec: WebsiteSpec, theme: "ResolvedTheme") -> str:
        """Fallback for empty specs."""
        return self._wrap_page(
            spec, theme,
            f"""  <main class="min-h-screen flex items-center justify-center">
    <div class="text-center">
      <h1 class="text-4xl font-bold mb-4">{spec.site_name}</h1>
      <p class="opacity-60">Website generation in progress...</p>
    </div>
  </main>""",
        )
