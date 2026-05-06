from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


def get_llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", "ollama").strip().lower()


def get_ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").strip()


def get_ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen3:14b").strip()


def get_openai_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()


def get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-5.4-mini").strip()