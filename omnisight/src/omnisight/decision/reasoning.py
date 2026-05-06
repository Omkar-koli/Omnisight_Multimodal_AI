from __future__ import annotations

import json
import os
from typing import Any, Dict

from openai import OpenAI

from omnisight.llm.schemas import ReasoningOutput


def reason_about_product(evidence: Dict[str, Any]) -> ReasoningOutput:
    from omnisight.llm.reasoner import reason_about_product_with_provider
    return reason_about_product_with_provider(evidence)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def get_category_hint(category_slug: str) -> str:
    category_slug = (category_slug or "").strip().lower()

    if category_slug == "beauty_and_personal_care":
        return (
            "Beauty products should be more sensitive to review quality, product risk, and customer trust. "
            "Do not restock aggressively if review risk is meaningful unless stockout pressure is clearly strong."
        )

    if category_slug == "toys_and_games":
        return (
            "Toys can be more trend-sensitive and event-sensitive. "
            "Strong trend or demand can justify a more assertive restock decision."
        )

    if category_slug == "home_and_kitchen":
        return (
            "Home and kitchen products often behave more steadily. "
            "Inventory cover and demand consistency should matter more than hype alone."
        )

    return (
        "Use category context when choosing between restocking, monitoring, slowing replenishment, or holding."
    )


def build_decision_cues(evidence: Dict[str, Any]) -> dict[str, Any]:
    product = evidence.get("product", {}) or {}
    rules = evidence.get("rules", {}) or {}
    reviews = evidence.get("reviews", []) or []
    trends = evidence.get("trends", []) or []
    images = evidence.get("images", []) or []

    category_slug = str(
        product.get("category_slug")
        or rules.get("category_slug")
        or ""
    ).strip()

    return {
        "category_slug": category_slug,
        "category_hint": get_category_hint(category_slug),
        "baseline_action": str(rules.get("action", "")),
        "baseline_confidence": safe_float(rules.get("confidence", 0.7), 0.7),
        "days_to_stockout": safe_float(rules.get("days_to_stockout", 999.0), 999.0),
        "stockout_risk_score": safe_float(rules.get("stockout_risk_score", 0.0)),
        "overstock_risk_score": safe_float(rules.get("overstock_risk_score", 0.0)),
        "review_risk_score": safe_float(rules.get("review_risk_score", 0.0)),
        "trend_strength_score": safe_float(rules.get("trend_strength_score", 0.0)),
        "demand_strength_score": safe_float(rules.get("demand_strength_score", 0.0)),
        "review_evidence_count": len(reviews),
        "trend_evidence_count": len(trends),
        "image_evidence_count": len(images),
    }


SYSTEM_PROMPT = """
You are OmniSight, an AI decision-support analyst for e-commerce inventory planning.

Your job:
- reason about each product individually using its own evidence
- explain a recommendation using only the structured business evidence provided
- never invent facts that are not in the input
- use the deterministic recommendation as a reference, not as the default
- you may override the baseline in either direction when reviews, trends, demand, inventory, stockout timing, or category context support it
- do not default to MONITOR or HOLD just because evidence is mixed
- prefer a decisive recommendation when the stock flag, threshold, and trend direction support one
- confidence should reflect evidence strength, not cautiousness
- return only valid JSON
- do not include markdown
- do not include extra commentary
"""

USER_PROMPT_TEMPLATE = """
You are given one product's evidence package.

Decision cues:
{decision_cues_json}

Use:
1. Product information
2. Deterministic recommendation from the rules engine
3. Supporting review evidence
4. Supporting trend evidence
5. Optional image evidence

Your task:
- produce a final recommendation for this specific product
- explain why
- mention risks and opportunities
- mention caution flags if review quality, weak trend, or overstock/stockout pressures exist
- you may override the baseline recommendation in either direction if the evidence supports it
- do not stay conservative by default

How to think:
- Compare stockout risk vs overstock risk
- Use category context
- Use review evidence when quality risk matters
- Use trend and demand evidence when timing matters
- If evidence is strong, make a decisive call
- If evidence is mixed but still directionally meaningful, prefer RESTOCK_CAUTIOUSLY or SLOW_REPLENISHMENT over generic MONITOR
- Use HOLD only when inventory is clearly not worth moving yet
- Use MONITOR when the evidence is genuinely ambiguous, not as a default
- If stock is CRITICAL or LOW STOCK and trend is not clearly negative, do not hide behind HOLD
- If the evidence is imperfect but directionally clear, choose RESTOCK_CAUTIOUSLY instead of generic MONITOR
- Use HOLD only when inventory is clearly sufficient and demand or trend does not justify action

Confidence guidance:
- 0.55 to 0.68 = mixed evidence
- 0.69 to 0.82 = decent support
- 0.83 to 0.95 = strong support across multiple signals

Important:
- If trend evidence is missing, say so indirectly through caution or limited confidence.
- Do not hallucinate competitor data, supplier facts, or sales values not given below.
- Keep evidence tied to the provided input.
- Confidence must be between 0 and 1.

Return JSON with exactly these top-level keys:
product_id
title
final_action
confidence
reasoning_summary
key_risks
key_opportunities
supporting_evidence
caution_flags
follow_up_actions

Allowed final_action values:
RESTOCK_NOW
RESTOCK_CAUTIOUSLY
MONITOR
SLOW_REPLENISHMENT
CHECK_QUALITY_BEFORE_RESTOCK
HOLD

VERY IMPORTANT:
supporting_evidence must be a JSON array of OBJECTS, not strings.

Correct format:
"supporting_evidence": [
  {{"source": "rules", "summary": "Rule engine flagged moderate stockout pressure."}},
  {{"source": "review", "summary": "Retrieved reviews show mixed product quality sentiment."}}
]

Allowed source values:
product
review
trend
image
rules

Evidence package:
{evidence_json}
"""


def make_llm_client() -> OpenAI:
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1").strip()
    api_key = os.getenv("LLM_API_KEY", "ollama").strip() or "ollama"
    return OpenAI(base_url=base_url, api_key=api_key)


def get_model_name() -> str:
    return os.getenv("LLM_MODEL", "gemma3:12b").strip()


def extract_json(raw_text: str) -> dict[str, Any]:
    raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except Exception:
        pass

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = raw_text[start:end + 1]
        return json.loads(candidate)

    raise ValueError("No valid JSON object found in model response.")


def infer_source_from_text(text: str) -> str:
    t = text.lower()

    if "review" in t or "rating" in t or "customer" in t:
        return "review"
    if "trend" in t or "search" in t:
        return "trend"
    if "image" in t or "visual" in t or "photo" in t:
        return "image"
    if "rule" in t or "stockout" in t or "overstock" in t or "confidence" in t:
        return "rules"
    return "product"


def normalize_supporting_evidence(items: Any) -> list[dict[str, str]]:
    if items is None:
        return []

    normalized: list[dict[str, str]] = []

    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                source = str(item.get("source", "product")).strip().lower()
                summary = str(item.get("summary", "")).strip()

                if not summary:
                    continue

                if source not in {"product", "review", "trend", "image", "rules"}:
                    source = "product"

                normalized.append(
                    {
                        "source": source,
                        "summary": summary,
                    }
                )

            elif isinstance(item, str):
                summary = item.strip()
                if not summary:
                    continue

                normalized.append(
                    {
                        "source": infer_source_from_text(summary),
                        "summary": summary,
                    }
                )

    return normalized


def normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]

    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []

    return []


def normalize_action(action: Any, fallback: str = "MONITOR") -> str:
    allowed = {
        "RESTOCK_NOW",
        "RESTOCK_CAUTIOUSLY",
        "MONITOR",
        "SLOW_REPLENISHMENT",
        "CHECK_QUALITY_BEFORE_RESTOCK",
        "HOLD",
    }

    action_str = str(action).strip().upper()
    return action_str if action_str in allowed else fallback


def normalize_confidence(value: Any, fallback: float = 0.72) -> float:
    try:
        v = float(value)
        if v < 0:
            return 0.0
        if v > 1:
            return 1.0
        return v
    except Exception:
        return fallback


def normalize_parsed_output(parsed: dict[str, Any], evidence: Dict[str, Any]) -> dict[str, Any]:
    product = evidence.get("product", {}) or {}
    rules = evidence.get("rules", {}) or {}

    fallback_action = rules.get("action", "MONITOR")
    fallback_confidence = rules.get("confidence", 0.72)

    return {
        "product_id": str(parsed.get("product_id") or product.get("product_id") or ""),
        "title": str(parsed.get("title") or product.get("title") or ""),
        "final_action": normalize_action(parsed.get("final_action"), fallback=fallback_action),
        "confidence": normalize_confidence(parsed.get("confidence"), fallback=fallback_confidence),
        "reasoning_summary": str(parsed.get("reasoning_summary") or "No reasoning summary provided.").strip(),
        "key_risks": normalize_string_list(parsed.get("key_risks")),
        "key_opportunities": normalize_string_list(parsed.get("key_opportunities")),
        "supporting_evidence": normalize_supporting_evidence(parsed.get("supporting_evidence")),
        "caution_flags": normalize_string_list(parsed.get("caution_flags")),
        "follow_up_actions": normalize_string_list(parsed.get("follow_up_actions")),
    }


def reason_about_product_legacy(evidence: Dict[str, Any]) -> ReasoningOutput:
    client = make_llm_client()
    model = get_model_name()

    decision_cues = build_decision_cues(evidence)

    prompt = USER_PROMPT_TEMPLATE.format(
        decision_cues_json=json.dumps(decision_cues, ensure_ascii=False, default=str, indent=2),
        evidence_json=json.dumps(evidence, ensure_ascii=False, default=str, indent=2),
    )

    response = client.chat.completions.create(
        model=model,
        temperature=0.35,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    raw_text = response.choices[0].message.content or ""
    parsed = extract_json(raw_text)
    parsed = normalize_parsed_output(parsed, evidence)

    return ReasoningOutput.model_validate(parsed)