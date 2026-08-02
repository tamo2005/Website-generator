"""
core/config.py — Centralized configuration via Pydantic Settings

All environment variables are defined here. Use get_settings() to access them.
Phase 2: Added Redis, Celery, provider keys, feature flags, and profile support.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application Profile ──────────────────────────────────
    APP_PROFILE: Literal["development", "staging", "production"] = "development"

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://wg_user:wg_pass@localhost:5432/website_generator"

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ──────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "CHANGE-ME-generate-a-real-secret-with-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Email (Resend) ──────────────────────────────────────
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "noreply@yourdomain.com"

    # ── OAuth — Google ──────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/oauth/google/callback"

    # ── OAuth — GitHub ──────────────────────────────────────
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/oauth/github/callback"

    # ── AI Providers ─────────────────────────────────────────
    # OpenRouter (primary)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "moonshotai/kimi-k2.6:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_SITE_URL: str = "http://localhost:3000"
    OPENROUTER_APP_NAME: str = "AI Website Generator"
    OPENROUTER_REASONING_ENABLED: bool = False

    # Gemini (secondary — generous free tier)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Ollama (local development — zero cost)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # OpenAI (stubbed — future)
    OPENAI_API_KEY: str = ""

    # Anthropic (stubbed — future)
    ANTHROPIC_API_KEY: str = ""

    # Default provider selection
    DEFAULT_PROVIDER: str = "openrouter"  # "openrouter" | "gemini" | "ollama"

    # ── Generation Parameters ────────────────────────────────
    TEMPERATURE: float = 0.6
    TOP_P: float = 0.95
    MAX_NEW_TOKENS: int = 4096

    # ── AI Cache ─────────────────────────────────────────────
    AI_CACHE_TTL_SECONDS: int = 3600
    AI_CACHE_MIN_PROMPT_LENGTH: int = 10

    # ── Pipeline ─────────────────────────────────────────────
    MAX_REPAIR_ATTEMPTS: int = 2
    PIPELINE_VERSION: str = "V1"

    # ── Application ─────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGIN: str = "http://localhost:3000,http://localhost:3001"
    MAX_PROMPT_CHARS: int = 8000

    # ── Feature Flags ────────────────────────────────────────
    ENABLE_COMPONENTS: bool = True        # Component-based generation
    ENABLE_HTML_VALIDATOR: bool = True    # HTML structure validation
    ENABLE_VALIDATOR_ACCESSIBILITY: bool = True
    ENABLE_VALIDATOR_SEO: bool = True
    ENABLE_VALIDATOR_SECURITY: bool = True
    ENABLE_VALIDATOR_PERFORMANCE: bool = True
    ENABLE_VALIDATOR_BEST_PRACTICES: bool = True
    ENABLE_REPAIR: bool = True            # AI self-repair loop
    ENABLE_AI_CACHE: bool = False         # Off by default in dev (easier debugging)
    ENABLE_METRICS: bool = True           # AI metrics tracking
    ENABLE_PIPELINE_EVENTS: bool = True   # Log pipeline events
    ENABLE_MEMORY: bool = False           # Phase 4
    ENABLE_EXPORT_REACT: bool = False     # Phase 3
    ENABLE_EXPORT_VUE: bool = False       # Phase 3
    ENABLE_EXPORT_NEXTJS: bool = False    # Phase 3


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings instance. Call get_settings.cache_clear() in tests."""
    return Settings()
