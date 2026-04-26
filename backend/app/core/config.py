from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode


class Settings(BaseSettings):
    # ─── Application ──────────────────────────────────────────────────────────
    api_version: str = "0.4.0"
    # 'development' enables /docs, verbose error detail, auto-create tables.
    # 'production' disables /docs, hides tracebacks, requires Alembic migrations.
    environment: Literal["development", "production"] = "development"
    debug: bool = False

    # Public origin of this API — used in sitemap absolute URLs.
    public_url: str = "http://localhost:8000"
    # Public origin of the frontend — used in sitemaps, OG metadata, links.
    frontend_url: str = "http://localhost:3000"

    # ─── CORS ─────────────────────────────────────────────────────────────────
    # Override via CORS_ORIGINS env var (comma-separated).
    # The Vercel frontend URL MUST be added here in production.
    # NoDecode skips pydantic-settings' default JSON parsing so the raw env
    # string reaches our validator below — that's what lets ops use the
    # comma-separated format instead of JSON.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ]

    # ─── Rate limiting ────────────────────────────────────────────────────────
    # slowapi format: "<n>/<period>" e.g. "20/minute", "200/hour"
    # Search endpoint hits Ollama (expensive) — keep tight by default.
    rate_limit_search: str = "20/minute"
    # Read endpoints are cheap; default is generous.
    rate_limit_default: str = "120/minute"

    # ─── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/exercise-identifier"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v: object) -> object:
        # Support CORS_ORIGINS=https://a.com,https://b.com  (comma form)
        # in addition to JSON-array form. Pydantic-settings only parses JSON
        # lists by default; this lets ops set the env var the obvious way.
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    # ─── Ollama ───────────────────────────────────────────────────────────────
    ollama_host: str = "http://localhost:11434"
    ollama_embed_model: str = "nomic-embed-text"
    # Judge model used for LLM re-ranking — must be pulled locally:
    #   ollama pull gemma4:e4b
    ollama_judge_model: str = "gemma4:e4b"
    # Hard timeout (seconds) for the judge LLM call; triggers vector fallback
    ollama_judge_timeout: float = 8.0
    # Hard timeout for embedding calls
    ollama_embed_timeout: float = 5.0

    # ─── ChromaDB ─────────────────────────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection: str = "exercise_descriptions"

    # ─── AWS / S3 (Phase 2) ───────────────────────────────────────────────────
    # aws_region: str = "us-east-1"
    # s3_ephemeral_bucket: str = "exercise-id-ephemeral"
    # s3_presigned_url_expiry: int = 60  # seconds
    # s3_object_lifecycle_minutes: int = 5

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
