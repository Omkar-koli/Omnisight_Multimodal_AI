from openai import OpenAI
from omnisight.settings import settings


def get_model_name() -> str:
    if settings.LLM_PROVIDER.lower() == "openai":
        return settings.OPENAI_MODEL
    return settings.LLM_MODEL


def make_llm_client() -> OpenAI:
    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        return OpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
        )

    if provider == "openai":
        return OpenAI(
            api_key=settings.OPENAI_API_KEY,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{settings.LLM_PROVIDER}'. "
        f"Use 'ollama' or 'openai'."
    )