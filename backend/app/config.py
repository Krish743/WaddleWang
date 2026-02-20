"""Application configuration from environment variables."""
import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for PolicyAssist backend. Set via env vars or .env file."""

    # LLM (use any OpenAI-compatible API)
    api_key: str = Field(default="", env=["API_KEY", "OPENAI_API_KEY"])
    base_url: str | None = Field(default=None, env=["BASE_URL", "OPENAI_BASE_URL"])  # e.g. for Groq: https://api.groq.com/openai/v1
    llm_model: str = "llama-3.1-70b-versatile"  # For Groq: llama-3.1-70b-versatile, mixtral-8x7b-32768, etc.

    # Embeddings
    embedding_provider: str = "huggingface"  # "huggingface" or "openai"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"  # Hugging Face model or OpenAI model name
    embedding_api_key: str | None = None  # Only needed for OpenAI embeddings
    embedding_base_url: str | None = None  # Only needed for OpenAI embeddings

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    # Document processing
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Persistence
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    chroma_persist_dir: Path = Path(__file__).resolve().parent.parent / "data" / "chroma"


def get_settings() -> Settings:
    return Settings()
