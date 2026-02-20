"""Embedding model wrapper (OpenAI-compatible API)."""
from langchain_openai import OpenAIEmbeddings

from app.config import get_settings


def get_embeddings():
    """Create embeddings client from settings."""
    s = get_settings()
    kwargs = {"model": s.embedding_model}
    if s.openai_base_url:
        kwargs["openai_api_base"] = s.openai_base_url
    return OpenAIEmbeddings(api_key=s.openai_api_key, **kwargs)
