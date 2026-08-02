"""
ai/assets/provider.py — Phase 6: Asset Provider System

Replaces empty placeholders with real, high-quality images.

Architecture:
    AssetProvider (ABC)
        ↓
    UnsplashSourceProvider  — Free, no API key, rate-limited
        ↓
    LocalAssetProvider      — Curated fallback URLs by category
        ↓
    CachingAssetProvider    — LRU cache wrapper

Each component requests assets via the provider:
    Hero → "business technology" → 1 image → provider → real URL

Usage:
    provider = get_default_asset_provider()
    images = provider.get_images("business technology", count=3)
"""
from __future__ import annotations

import hashlib
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

logger = logging.getLogger("ai-site-gen")


# ══════════════════════════════════════════════════════════════════════════════
# ASSET IMAGE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class AssetImage:
    """A resolved image asset."""
    url: str
    alt: str
    width: int = 1200
    height: int = 800
    attribution: str = ""
    source: str = "unsplash"

    def to_img_tag(self, extra_classes: str = "", loading: str = "lazy") -> str:
        """Generate an HTML <img> tag."""
        return (
            f'<img src="{self.url}" alt="{self.alt}" '
            f'width="{self.width}" height="{self.height}" '
            f'loading="{loading}" class="w-full h-full object-cover {extra_classes}" />'
        )


# ══════════════════════════════════════════════════════════════════════════════
# BASE PROVIDER
# ══════════════════════════════════════════════════════════════════════════════

class AssetProvider(ABC):
    """Abstract base class for image asset providers."""

    @abstractmethod
    def get_images(self, query: str, count: int = 1) -> list[AssetImage]:
        """Get images matching a query."""
        ...

    def get_hero_image(self, industry: str) -> AssetImage:
        """Get a single hero image for an industry."""
        images = self.get_images(f"{industry} hero", count=1)
        return images[0] if images else self._placeholder(industry)

    def get_team_avatars(self, count: int = 4) -> list[AssetImage]:
        """Get team member avatar images."""
        return self.get_images("professional portrait headshot", count=count)

    def get_gallery_images(self, industry: str, count: int = 6) -> list[AssetImage]:
        """Get gallery images for an industry."""
        return self.get_images(f"{industry} gallery", count=count)

    def get_logo_placeholders(self, count: int = 6) -> list[AssetImage]:
        """Get placeholder company logo images."""
        return self.get_images("company logo minimal", count=count)

    @staticmethod
    def _placeholder(alt: str = "Image") -> AssetImage:
        return AssetImage(
            url="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='600' fill='%23334155'%3E%3Crect width='800' height='600'/%3E%3Ctext x='50%25' y='50%25' fill='%2364748b' font-size='24' text-anchor='middle' dy='.3em'%3EImage%3C/text%3E%3C/svg%3E",
            alt=alt,
            source="placeholder",
        )


# ══════════════════════════════════════════════════════════════════════════════
# UNSPLASH SOURCE PROVIDER (Free, no API key)
# ══════════════════════════════════════════════════════════════════════════════

class UnsplashSourceProvider(AssetProvider):
    """
    Uses Unsplash Source (free, no API key needed).

    URLs: https://images.unsplash.com/photo-{id}?w={w}&h={h}&fit=crop
    We use curated photo IDs for reliability instead of random queries.
    """

    # Curated photo IDs by category (real Unsplash photo IDs)
    CURATED_PHOTOS: dict[str, list[str]] = {
        "technology": [
            "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1488590528505-98d2b5aba04b?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&h=800&fit=crop",
        ],
        "business": [
            "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1497366811353-6870744d04b2?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1553877522-43269d4ea984?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=1200&h=800&fit=crop",
        ],
        "food": [
            "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=1200&h=800&fit=crop",
        ],
        "nature": [
            "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=1200&h=800&fit=crop",
        ],
        "people": [
            "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1543269865-cbf427effbad?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=1200&h=800&fit=crop",
        ],
        "portrait": [
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop",
            "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=400&fit=crop",
            "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&h=400&fit=crop",
            "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&h=400&fit=crop",
            "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=400&fit=crop",
            "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=400&fit=crop",
            "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=400&fit=crop",
            "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=400&h=400&fit=crop",
        ],
        "abstract": [
            "https://images.unsplash.com/photo-1557672172-298e090bd0f1?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1618005198919-d3d4b5a92ead?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1614850523296-d8c1af93d400?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1620421680010-0766ff230392?w=1200&h=800&fit=crop",
        ],
        "creative": [
            "https://images.unsplash.com/photo-1561070791-2526d30994b5?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1558655146-d09347e92766?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1626785774573-4b799315345d?w=1200&h=800&fit=crop",
            "https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=1200&h=800&fit=crop",
        ],
    }

    # Industry → category mapping
    INDUSTRY_MAP: dict[str, str] = {
        "ai": "technology", "tech": "technology", "technology": "technology",
        "saas": "technology", "software": "technology", "startup": "technology",
        "food": "food", "restaurant": "food", "cafe": "food", "bakery": "food",
        "finance": "business", "consulting": "business", "corporate": "business",
        "marketing": "creative", "agency": "creative", "design": "creative",
        "health": "nature", "wellness": "nature", "fitness": "nature",
    }

    def get_images(self, query: str, count: int = 1) -> list[AssetImage]:
        category = self._resolve_category(query)
        photos = self.CURATED_PHOTOS.get(category, self.CURATED_PHOTOS["technology"])

        # Deterministic but varied selection based on query
        seed = int(hashlib.md5(query.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        selected = rng.sample(photos, min(count, len(photos)))

        return [
            AssetImage(
                url=url,
                alt=f"{query} image",
                width=1200 if "w=1200" in url else 400,
                height=800 if "h=800" in url else 400,
                attribution="Unsplash",
                source="unsplash",
            )
            for url in selected
        ]

    def get_team_avatars(self, count: int = 4) -> list[AssetImage]:
        photos = self.CURATED_PHOTOS["portrait"]
        selected = photos[:min(count, len(photos))]
        names = ["Sarah Chen", "Marcus Johnson", "Aisha Patel", "David Kim",
                 "Emily Rodriguez", "James Wilson", "Priya Sharma", "Alex Thompson"]
        return [
            AssetImage(
                url=url, alt=f"{names[i]} portrait",
                width=400, height=400, source="unsplash",
            )
            for i, url in enumerate(selected)
        ]

    def _resolve_category(self, query: str) -> str:
        q = query.lower()
        for keyword, category in self.INDUSTRY_MAP.items():
            if keyword in q:
                return category
        if "portrait" in q or "avatar" in q or "headshot" in q:
            return "portrait"
        if "abstract" in q or "gradient" in q:
            return "abstract"
        if "food" in q or "restaurant" in q:
            return "food"
        return "technology"


# ══════════════════════════════════════════════════════════════════════════════
# LOCAL FALLBACK PROVIDER
# ══════════════════════════════════════════════════════════════════════════════

class LocalAssetProvider(AssetProvider):
    """Generates SVG placeholder images with gradient backgrounds. Zero network calls."""

    GRADIENT_PALETTES = [
        ("4f46e5", "7c3aed"),  # Indigo → Violet
        ("0ea5e9", "6366f1"),  # Sky → Indigo
        ("10b981", "06b6d4"),  # Emerald → Cyan
        ("f59e0b", "ef4444"),  # Amber → Red
        ("ec4899", "8b5cf6"),  # Pink → Violet
        ("14b8a6", "3b82f6"),  # Teal → Blue
    ]

    def get_images(self, query: str, count: int = 1) -> list[AssetImage]:
        images = []
        for i in range(count):
            idx = i % len(self.GRADIENT_PALETTES)
            c1, c2 = self.GRADIENT_PALETTES[idx]
            svg = (
                f"<svg xmlns='http://www.w3.org/2000/svg' width='1200' height='800'>"
                f"<defs><linearGradient id='g{i}' x1='0%' y1='0%' x2='100%' y2='100%'>"
                f"<stop offset='0%' stop-color='%23{c1}'/>"
                f"<stop offset='100%' stop-color='%23{c2}'/>"
                f"</linearGradient></defs>"
                f"<rect width='1200' height='800' fill='url(%23g{i})'/>"
                f"</svg>"
            )
            url = f"data:image/svg+xml,{svg}"
            images.append(AssetImage(url=url, alt=query, source="local"))
        return images


# ══════════════════════════════════════════════════════════════════════════════
# CACHING WRAPPER
# ══════════════════════════════════════════════════════════════════════════════

class CachingAssetProvider(AssetProvider):
    """Wraps any AssetProvider with an in-memory cache."""

    def __init__(self, inner: AssetProvider, max_size: int = 128) -> None:
        self._inner = inner
        self._cache: dict[str, list[AssetImage]] = {}
        self._max_size = max_size

    def get_images(self, query: str, count: int = 1) -> list[AssetImage]:
        key = f"{query}::{count}"
        if key in self._cache:
            return self._cache[key]
        result = self._inner.get_images(query, count)
        if len(self._cache) < self._max_size:
            self._cache[key] = result
        return result


# ══════════════════════════════════════════════════════════════════════════════
# FACTORY
# ══════════════════════════════════════════════════════════════════════════════

def get_default_asset_provider() -> AssetProvider:
    """Get the default asset provider (Unsplash Source with caching)."""
    return CachingAssetProvider(UnsplashSourceProvider())
