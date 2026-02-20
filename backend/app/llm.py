"""LLM client for answers and summaries (OpenAI-compatible API)."""
from langchain_openai import ChatOpenAI

from app.config import get_settings


def get_llm():
    """Create LLM from settings."""
    s = get_settings()
    kwargs = {"model": s.llm_model, "temperature": 0}
    if s.base_url:
        kwargs["openai_api_base"] = s.base_url
    return ChatOpenAI(api_key=s.api_key, **kwargs)
