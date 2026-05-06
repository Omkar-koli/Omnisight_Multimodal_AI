from __future__ import annotations

from typing import Any, Dict

from omnisight.decision.reasoning import reason_about_product_legacy
from omnisight.llm.schemas import ReasoningOutput


def reason_with_ollama(evidence: Dict[str, Any]) -> ReasoningOutput:
    return reason_about_product_legacy(evidence)