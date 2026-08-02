"""
ai/core/config_profiles.py — Per-environment AI configuration profiles

Each profile defines environment-specific AI behavior:
  - development: No cache, verbose logging, 1 repair attempt, Ollama-friendly
  - staging:     Cache enabled, normal repair, full logging
  - production:  Cache enabled, 2 repair attempts, warning-level logging only

Phase 2: Referenced by the DI container (ai/core/container.py) and baked into
feature flag evaluation at runtime. The active profile is set via APP_PROFILE env var.
"""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel


class ConfigProfile(str, Enum):
    DEVELOPMENT = "development"
    STAGING     = "staging"
    PRODUCTION  = "production"


class ProfileSettings(BaseModel):
    """Per-environment AI settings overlay (not a replacement for core.config)."""
    default_provider: str
    default_model_hint: str      # Suggestion — actual model still from .env
    enable_cache: bool
    enable_repair: bool
    max_repair_attempts: int
    log_pipeline_events: bool    # Log every PipelineEvent inline
    log_level: str               # Python logging level string


PROFILES: dict[ConfigProfile, ProfileSettings] = {
    ConfigProfile.DEVELOPMENT: ProfileSettings(
        default_provider="openrouter",
        default_model_hint="moonshotai/kimi-k2.6:free",
        enable_cache=False,          # Cache off — easier to debug
        enable_repair=True,
        max_repair_attempts=1,       # 1 attempt in dev — faster iteration
        log_pipeline_events=True,    # Every event logged inline
        log_level="DEBUG",
    ),
    ConfigProfile.STAGING: ProfileSettings(
        default_provider="openrouter",
        default_model_hint="moonshotai/kimi-k2.6:free",
        enable_cache=True,
        enable_repair=True,
        max_repair_attempts=2,
        log_pipeline_events=True,    # Staged: still useful for debugging
        log_level="INFO",
    ),
    ConfigProfile.PRODUCTION: ProfileSettings(
        default_provider="openrouter",
        default_model_hint="moonshotai/kimi-k2.6:free",
        enable_cache=True,
        enable_repair=True,
        max_repair_attempts=2,
        log_pipeline_events=False,   # Events recorded async to metrics table, not inline
        log_level="WARNING",
    ),
}


def get_profile(name: str) -> ProfileSettings:
    """Return the ProfileSettings for the given profile name string."""
    try:
        return PROFILES[ConfigProfile(name)]
    except (KeyError, ValueError):
        return PROFILES[ConfigProfile.DEVELOPMENT]
