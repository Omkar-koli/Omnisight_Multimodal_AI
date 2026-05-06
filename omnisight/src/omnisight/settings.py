from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "OmniSight"
    APP_ENV: str = "dev"
    DEBUG: bool = True

    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "gemma3:4b"
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_API_KEY: str = "ollama"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    OLLAMA_API_BASE: str = "http://localhost:11434"

    TEXT_EMBED_PROVIDER: str = "ollama"
    TEXT_EMBED_MODEL: str = "embeddinggemma"
    MM_EMBED_MODEL: str = "clip-ViT-B-32"

    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_PRODUCTS_TEXT: str = "products_text"
    QDRANT_COLLECTION_REVIEWS_TEXT: str = "reviews_text"
    QDRANT_COLLECTION_TRENDS_TEXT: str = "trends_text"
    QDRANT_COLLECTION_PRODUCTS_MM: str = "products_mm"

    DATA_DIR: str = "./data"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def data_path(self) -> Path:
        return Path(self.DATA_DIR)


settings = Settings()