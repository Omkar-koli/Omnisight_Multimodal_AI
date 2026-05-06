from __future__ import annotations

from typing import Any, Dict

from omnisight.llm.provider_config import get_llm_provider
from omnisight.llm.schemas import ReasoningOutput
from omnisight.llm.openai_reasoner import reason_with_openai
from omnisight.llm.ollama_reasoner import reason_with_ollama


def reason_about_product_with_provider(evidence: Dict[str, Any]) -> ReasoningOutput:
    provider = get_llm_provider()

    if provider == "openai":
        return reason_with_openai(evidence)

    if provider == "ollama":
        return reason_with_ollama(evidence)

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")