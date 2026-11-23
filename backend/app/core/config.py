"""
Application configuration using pydantic-settings.

Loads settings from environment variables and .env file.
"""

from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/careerpilot.db"

    # ── LLM Providers ───────────────────────────────────────────────────
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.1-70b-versatile"

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    XAI_API_KEY: Optional[str] = None
    GROK_MODEL: str = "grok-4.7"

    LLM_PROVIDER_PRIORITY: str = "gemini,xai,groq"

    # ── SearXNG Search ──────────────────────────────────────────────────
    SEARXNG_URL: str = "http://localhost:8888"
    SEARXNG_ENABLED: bool = False

    # ── Application ─────────────────────────────────────────────────────
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_DEBUG: bool = False

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    SECRET_KEY: str = "change-me-in-production-use-a-real-secret-key"

    # ── File Uploads ────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_UPLOAD_TYPES: str = ".pdf,.docx,.txt"

    # ── MCP Server ──────────────────────────────────────────────────────
    MCP_SERVER_HOST: str = "0.0.0.0"
    MCP_SERVER_PORT: int = 8001

    # ── Computed helpers ────────────────────────────────────────────────
    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_upload_types_list(self) -> List[str]:
        """Return allowed upload types as a list."""
        return [t.strip() for t in self.ALLOWED_UPLOAD_TYPES.split(",") if t.strip()]

    @property
    def llm_provider_priority_list(self) -> List[str]:
        """Return LLM provider priority as a list."""
        return [p.strip() for p in self.LLM_PROVIDER_PRIORITY.split(",") if p.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        """Return max upload size in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
