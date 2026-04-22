"""Environment-driven settings.

pydantic-settings picks up values from environment variables or a `.env`
file at the backend root. Keep this small — any setting that graduates
beyond dev defaults should come through here, not via module-level
os.environ reads sprinkled in the codebase.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Instantiate via `get_settings()`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Postgres (async). Default targets Homebrew-style macOS install with
    # trust auth (no password, role == OS user). Override via DATABASE_URL
    # in `.env` or the process environment.
    database_url: str = Field(
        default="postgresql+asyncpg://samuelshine@localhost:5432/exercise_identifier",
        description="SQLAlchemy async URL for the primary Postgres DB.",
    )

    # Vector DB — populated once we pick a provider. Keeping the fields
    # here so calling code has a stable shape to read from.
    vector_db_provider: str = Field(default="pinecone")
    vector_db_index: str = Field(default="exercises")
    vector_db_api_key: str | None = Field(default=None)

    # SQL echo is noisy; default off, flip on for debugging.
    db_echo: bool = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor. FastAPI dependency-friendly."""
    return Settings()
