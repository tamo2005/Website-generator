"""
ai/assets/svg_assets.py — Phase 6: SVG Asset Generators

Provides inline SVG assets for components that need:
  - Icons (star, check, arrow, quote, mail, etc.)
  - Avatar placeholders (initials-based)
  - Company logo placeholders
  - Background patterns (dots, grid, waves, gradient mesh)

All SVGs are inline — zero external dependencies, zero network calls.

Usage:
    from ai.assets.svg_assets import SVGIcons, AvatarGenerator, PatternGenerator
    icon = SVGIcons.get("star")
    avatar = AvatarGenerator.generate("John Doe", "#6366f1")
"""
from __future__ import annotations

import hashlib


# ══════════════════════════════════════════════════════════════════════════════
# SVG ICON LIBRARY
# ══════════════════════════════════════════════════════════════════════════════

class SVGIcons:
    """Inline SVG icons — Lucide-inspired, 24x24 viewBox."""

    _ICONS: dict[str, str] = {
        "star": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
        "star-filled": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
        "check": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
        "check-circle": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        "x": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
        "arrow-right": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>',
        "arrow-up-right": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></svg>',
        "chevron-down": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>',
        "chevron-right": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>',
        "menu": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>',
        "mail": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
        "phone": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
        "map-pin": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
        "quote": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10h-9.983zm-14.017 0v-7.391c0-5.704 3.748-9.57 9-10.609l.996 2.151c-2.433.917-3.996 3.638-3.996 5.849h3.983v10h-9.983z"/></svg>',
        "zap": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
        "shield": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
        "sparkles": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/></svg>',
        "rocket": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>',
        "globe": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
        "clock": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
        "users": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
        "trending-up": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
        "code": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
        "layers": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
        "lock": '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    }

    @classmethod
    def get(cls, name: str, size: int = 24, color: str = "currentColor") -> str:
        """Get an SVG icon by name. Returns empty string if not found."""
        svg = cls._ICONS.get(name, "")
        if svg and size != 24:
            svg = svg.replace('width="24"', f'width="{size}"')
            svg = svg.replace('height="24"', f'height="{size}"')
        if svg and color != "currentColor":
            svg = svg.replace('stroke="currentColor"', f'stroke="{color}"')
            svg = svg.replace('fill="currentColor"', f'fill="{color}"')
        return svg

    @classmethod
    def list_icons(cls) -> list[str]:
        """List all available icon names."""
        return sorted(cls._ICONS.keys())

    @classmethod
    def get_feature_icons(cls, count: int = 6) -> list[str]:
        """Get a set of feature-appropriate icons."""
        feature_icons = [
            "zap", "shield", "rocket", "globe", "clock", "users",
            "trending-up", "code", "layers", "lock", "sparkles", "check-circle",
        ]
        return feature_icons[:min(count, len(feature_icons))]


# ══════════════════════════════════════════════════════════════════════════════
# AVATAR GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class AvatarGenerator:
    """Generates SVG avatar placeholders with initials."""

    COLORS = [
        "#6366f1", "#8b5cf6", "#ec4899", "#ef4444", "#f59e0b",
        "#10b981", "#06b6d4", "#3b82f6", "#14b8a6", "#f97316",
    ]

    @classmethod
    def generate(
        cls,
        name: str,
        color: str | None = None,
        size: int = 48,
    ) -> str:
        """Generate an SVG avatar with initials."""
        initials = cls._get_initials(name)
        bg = color or cls._color_for_name(name)
        font_size = size * 0.4

        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" rx="{size // 2}" fill="{bg}"/>'
            f'<text x="50%" y="50%" dy=".1em" fill="white" font-family="Inter, system-ui, sans-serif" '
            f'font-size="{font_size}" font-weight="600" text-anchor="middle" dominant-baseline="middle">'
            f'{initials}</text></svg>'
        )

    @classmethod
    def generate_data_uri(cls, name: str, color: str | None = None, size: int = 48) -> str:
        """Generate a data URI for inline use in img src."""
        svg = cls.generate(name, color, size)
        encoded = svg.replace('"', "'").replace("#", "%23").replace("<", "%3C").replace(">", "%3E")
        return f"data:image/svg+xml,{encoded}"

    @classmethod
    def _get_initials(cls, name: str) -> str:
        parts = name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return name[:2].upper() if name else "?"

    @classmethod
    def _color_for_name(cls, name: str) -> str:
        idx = int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % len(cls.COLORS)
        return cls.COLORS[idx]


# ══════════════════════════════════════════════════════════════════════════════
# LOGO GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class LogoGenerator:
    """Generates minimal SVG company logo placeholders."""

    SHAPES = [
        # Circle with initial
        lambda name, color, size: (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<circle cx="{size//2}" cy="{size//2}" r="{size//2 - 2}" fill="{color}" opacity="0.15"/>'
            f'<text x="50%" y="50%" dy=".1em" fill="{color}" font-family="Inter, system-ui, sans-serif" '
            f'font-size="{size * 0.45}" font-weight="700" text-anchor="middle" dominant-baseline="middle">'
            f'{name[0].upper()}</text></svg>'
        ),
        # Rounded square with initial
        lambda name, color, size: (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" rx="{size//4}" fill="{color}" opacity="0.12"/>'
            f'<text x="50%" y="50%" dy=".1em" fill="{color}" font-family="Inter, system-ui, sans-serif" '
            f'font-size="{size * 0.4}" font-weight="700" text-anchor="middle" dominant-baseline="middle">'
            f'{name[:2].upper()}</text></svg>'
        ),
    ]

    COLORS = [
        "#6366f1", "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
        "#8b5cf6", "#ec4899", "#06b6d4", "#14b8a6", "#f97316",
    ]

    @classmethod
    def generate(cls, company_name: str, size: int = 40) -> str:
        """Generate a company logo placeholder SVG."""
        idx = int(hashlib.md5(company_name.encode()).hexdigest()[:8], 16)
        color = cls.COLORS[idx % len(cls.COLORS)]
        shape_fn = cls.SHAPES[idx % len(cls.SHAPES)]
        return shape_fn(company_name, color, size)

    @classmethod
    def generate_set(cls, company_names: list[str], size: int = 40) -> list[str]:
        """Generate a set of company logo SVGs."""
        return [cls.generate(name, size) for name in company_names]


# ══════════════════════════════════════════════════════════════════════════════
# PATTERN GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class PatternGenerator:
    """Generates SVG background patterns."""

    @staticmethod
    def dots(color: str = "rgba(255,255,255,0.05)", spacing: int = 24, radius: int = 1) -> str:
        """Dot grid pattern."""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{spacing}" height="{spacing}">'
            f'<circle cx="{spacing//2}" cy="{spacing//2}" r="{radius}" fill="{color}"/></svg>'
        )

    @staticmethod
    def grid(color: str = "rgba(255,255,255,0.03)", spacing: int = 48) -> str:
        """Grid lines pattern."""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{spacing}" height="{spacing}">'
            f'<path d="M {spacing} 0 L 0 0 0 {spacing}" fill="none" stroke="{color}" stroke-width="1"/></svg>'
        )

    @staticmethod
    def diagonal(color: str = "rgba(255,255,255,0.02)", spacing: int = 10) -> str:
        """Diagonal lines pattern."""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{spacing}" height="{spacing}">'
            f'<path d="M0,{spacing} l{spacing},-{spacing} M-{spacing//4},{spacing//4} l{spacing//2},-{spacing//2} '
            f'M{3*spacing//4},{5*spacing//4} l{spacing//2},-{spacing//2}" '
            f'stroke="{color}" stroke-width="1"/></svg>'
        )

    @classmethod
    def get_css_background(cls, pattern_type: str = "dots", color: str = "rgba(255,255,255,0.05)") -> str:
        """Get a CSS background-image property value for a pattern."""
        generators = {
            "dots": cls.dots,
            "grid": cls.grid,
            "diagonal": cls.diagonal,
        }
        gen = generators.get(pattern_type, cls.dots)
        svg = gen(color)
        encoded = svg.replace('"', "'").replace("#", "%23").replace("<", "%3C").replace(">", "%3E")
        return f"url(\"data:image/svg+xml,{encoded}\")"
