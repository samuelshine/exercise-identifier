from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/exercise_identifier"
    db_echo: bool = False

    ollama_host: str = "http://localhost:11434"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_judge_model: str = "gemma4:e4b"

    chroma_persist_dir: str = "./chroma_db"
    chroma_collection: str = "exercise_descriptions"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
