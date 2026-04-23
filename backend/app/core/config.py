from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ─── Application ──────────────────────────────────────────────────────────
    api_version: str = "0.4.0"
    debug: bool = False

    # ─── CORS ─────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins; override via CORS_ORIGINS env var.
    # The Vercel frontend URL must be added here in production.
    cors_origins: list[str] = [
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ]

    # ─── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/exercise_identifier"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

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
