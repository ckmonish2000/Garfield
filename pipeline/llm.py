from __future__ import annotations

from langchain_core.language_models import BaseChatModel


def get_llm(config: dict) -> BaseChatModel:
    """Create an LLM instance based on config. Provider-agnostic factory."""
    provider = config.get("llm_provider", "openai")
    model = config.get("llm_model", "gpt-4o")

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, temperature=0)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, temperature=0)
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, temperature=0)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
