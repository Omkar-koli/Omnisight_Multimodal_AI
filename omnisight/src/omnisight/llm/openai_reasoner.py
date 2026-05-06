from __future__ import annotations

import json
from typing import Any, Dict

from openai import OpenAI

from omnisight.llm.provider_config import get_openai_api_key, get_openai_model
from omnisight.llm.schemas import ReasoningOutput


SYSTEM_PROMPT = """
You are OmniSight, an AI decision-support analyst for e-commerce inventory planning.

Rules:
- Use only the provided evidence.
- Do not invent missing facts.
- Prefer the deterministic rule recommendation unless the evidence suggests caution.
- Return a structured decision object only.
"""

USER_TEMPLATE = """
You are given one product evidence package.

Task:
- produce a final recommendation
- explain why
- mention risks and opportunities
- mention caution flags if relevant

Allowed final_action values:
RESTOCK_NOW
RESTOCK_CAUTIOUSLY
MONITOR
SLOW_REPLENISHMENT
CHECK_QUALITY_BEFORE_RESTOCK
HOLD

Evidence package:
{evidence_json}
"""


def reason_with_openai(evidence: Dict[str, Any]) -> ReasoningOutput:
    api_key = get_openai_api_key()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is missing in .env")

    client = OpenAI(api_key=api_key)
    model = get_openai_model()

    prompt = USER_TEMPLATE.format(
        evidence_json=json.dumps(evidence, ensure_ascii=False, default=str, indent=2)
    )

    response = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        text_format=ReasoningOutput,
    )

    parsed = response.output_parsed
    if parsed is None:
        raise ValueError("OpenAI returned no parsed structured output.")

    return parsed