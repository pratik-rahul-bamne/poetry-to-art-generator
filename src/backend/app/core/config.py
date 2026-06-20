"""
Core Configuration — pydantic-settings based.
All config comes from environment variables or .env file.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # src directory


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "AI Poem Visualizer"
    APP_VERSION: str = "2.0.0"
    APP_ENV: str = "development"  # development | production
    DEBUG: bool = True

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'poem_visualizer.db'}"

    # ── JWT Security ─────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ── AI Providers ─────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    NLP_PROVIDER: str = "gemini"          # gemini | flan-t5 | fallback
    IMAGE_PROVIDER: str = "pollinations"  # pollinations | stable-diffusion | huggingface
    HF_API_TOKEN: str = ""

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_GUEST: int = 10       # requests per hour for guests
    RATE_LIMIT_REGISTERED: int = 50  # requests per hour for registered users

    # ── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["*"]

    # ── Paths ─────────────────────────────────────────────────────────────────
    OUTPUTS_DIR: Path = BASE_DIR / "outputs"
    ASSETS_DIR: Path = BASE_DIR / "assets"
    LOGS_DIR: Path = BASE_DIR / "logs"

    @field_validator("OUTPUTS_DIR", "ASSETS_DIR", "LOGS_DIR", mode="before")
    @classmethod
    def ensure_path(cls, v):
        p = Path(v)
        p.mkdir(parents=True, exist_ok=True)
        return p


# Singleton instance
settings = Settings()
