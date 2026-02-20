"""Embedding model wrapper - supports Hugging Face and OpenAI."""
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings

from app.config import get_settings


def get_embeddings():
    """Create embeddings client from settings.
    Supports Hugging Face (local, no API key) or OpenAI embeddings.
    """
    s = get_settings()
    
    if s.embedding_provider.lower() == "huggingface":
        # Use Hugging Face embeddings (local, no API key needed)
        return HuggingFaceEmbeddings(
            model_name=s.embedding_model,
            model_kwargs={"device": "cpu"},  # Use "cuda" if GPU available
            encode_kwargs={"normalize_embeddings": True},  # Normalize for better similarity
        )
    elif s.embedding_provider.lower() == "openai":
        # Use OpenAI embeddings (requires API key)
        kwargs = {"model": s.embedding_model}
        
        api_key = s.embedding_api_key if s.embedding_api_key else s.api_key
        base_url = s.embedding_base_url if s.embedding_base_url else s.base_url
        
        if base_url:
            kwargs["openai_api_base"] = base_url
        
        if not api_key:
            raise ValueError(
                "OpenAI embeddings require an API key. Set EMBEDDING_API_KEY or API_KEY."
            )
        
        return OpenAIEmbeddings(api_key=api_key, **kwargs)
    else:
        raise ValueError(
            f"Unknown embedding provider: {s.embedding_provider}. "
            "Use 'huggingface' or 'openai'."
        )
