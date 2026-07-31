"""
core/config.py — Centralized configuration via Pydantic Settings

All environment variables are defined here. Use get_settings() to access them.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./website_generator.db"

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

    # ── OpenRouter ──────────────────────────────────────────
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "moonshotai/kimi-k2.6:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_SITE_URL: str = "http://localhost:3000"
    OPENROUTER_APP_NAME: str = "AI Website Generator"
    OPENROUTER_REASONING_ENABLED: bool = False
    TEMPERATURE: float = 0.6
    TOP_P: float = 0.95
    MAX_NEW_TOKENS: int = 2048

    # ── Application ─────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGIN: str = "http://localhost:3000,http://localhost:3001"
    MAX_PROMPT_CHARS: int = 8000


def get_settings() -> Settings:
    """Settings instance loaded from environment variables and .env file."""
    return Settings()
