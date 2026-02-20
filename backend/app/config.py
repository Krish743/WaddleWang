"""Application configuration from environment variables."""
import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for PolicyAssist backend. Set via env vars or .env file."""

    # LLM (use any OpenAI-compatible API)
    openai_api_key: str = ""
    openai_base_url: str | None = None  # e.g. for Azure or other providers
    llm_model: str = "gpt-4o-mini"

    # Embeddings
    embedding_model: str = "text-embedding-3-small"

    # Document processing
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Persistence
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    chroma_persist_dir: Path = Path(__file__).resolve().parent.parent / "data" / "chroma"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> Settings:
    return Settings()
