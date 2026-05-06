from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class OmniSightGraphState(TypedDict, total=False):
    product_id: str
    evidence: Dict[str, Any]
    llm_output: Dict[str, Any]
    final_response: Dict[str, Any]
    error: str