from __future__ import annotations

from typing import Any, Dict

from omnisight.decision.reasoning import reason_about_product
from omnisight.retrieval.evidence_builder import EvidenceBuilder


_BUILDER: EvidenceBuilder | None = None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def infer_baseline_action(rules: Dict[str, Any]) -> str:
    stock_flag = str(rules.get("stock_flag", "") or "")
    trend_classification = str(rules.get("trend_classification", "") or "")
    current_quantity = safe_float(rules.get("current_quantity", 0.0), 0.0)
    threshold_units = safe_float(rules.get("threshold_units", 0.0), 0.0)
    recommended_order_qty = safe_float(rules.get("recommended_order_qty", 0.0), 0.0)
    manual_review_required = bool(rules.get("manual_review_required", False))
    projected_weekly_demand = safe_float(rules.get("projected_weekly_demand", 0.0), 0.0)

    ratio = current_quantity / max(threshold_units, 1.0)
    weeks_cover = current_quantity / max(projected_weekly_demand, 1.0)

    if manual_review_required and recommended_order_qty > 0:
        return "CHECK_QUALITY_BEFORE_RESTOCK"

    if stock_flag == "CRITICAL":
        return "RESTOCK_NOW"

    if stock_flag == "LOW STOCK":
        return "RESTOCK_CAUTIOUSLY"

    if trend_classification == "Trending Up" and weeks_cover <= 3.0:
        return "RESTOCK_CAUTIOUSLY"

    if trend_classification == "Trending Down" and ratio >= 1.75:
        return "HOLD"

    if trend_classification == "Trending Down" and ratio >= 1.25:
        return "SLOW_REPLENISHMENT"

    return "MONITOR"


def infer_baseline_confidence(rules: Dict[str, Any]) -> float:
    if "confidence" in rules and rules.get("confidence") is not None:
        return round(safe_float(rules.get("confidence", 0.0), 0.0), 2)

    confidence_pct = safe_float(rules.get("confidence_pct", 0.0), 0.0)
    if confidence_pct > 0:
        return round(confidence_pct / 100.0, 2)

    return 0.60


def get_builder() -> EvidenceBuilder:
    global _BUILDER
    if _BUILDER is None:
        _BUILDER = EvidenceBuilder()
    return _BUILDER


def build_evidence_node(state: Dict[str, Any]) -> Dict[str, Any]:
    product_id = str(state.get("product_id", "")).strip()
    if not product_id:
        return {"error": "Missing product_id in graph state."}

    try:
        builder = get_builder()
        evidence = builder.build(product_id)
        return {"evidence": evidence}
    except Exception as e:
        return {"error": f"Evidence build failed: {e}"}


def reason_node(state: Dict[str, Any]) -> Dict[str, Any]:
    if state.get("error"):
        return {}

    evidence = state.get("evidence")
    if not evidence:
        return {"error": "Missing evidence for reasoning node."}

    try:
        result = reason_about_product(evidence)
        return {"llm_output": result.model_dump()}
    except Exception as e:
        return {"error": f"LLM reasoning failed: {e}"}


def format_output_node(state: Dict[str, Any]) -> Dict[str, Any]:
    if state.get("error"):
        return {
            "final_response": {
                "status": "error",
                "product_id": state.get("product_id", ""),
                "error": state["error"],
            }
        }

    evidence = state.get("evidence", {}) or {}
    llm_output = state.get("llm_output", {}) or {}

    product = evidence.get("product", {}) or {}
    rules = evidence.get("rules", {}) or {}

    baseline_action = str(rules.get("action", "") or "").strip()
    if not baseline_action:
        baseline_action = infer_baseline_action(rules)

    baseline_confidence = rules.get("confidence", None)
    if baseline_confidence in (None, "", 0, 0.0):
        baseline_confidence = infer_baseline_confidence(rules)
    else:
        baseline_confidence = round(safe_float(baseline_confidence, 0.0), 2)

    final_response = {
        "status": "ok",
        "product_id": llm_output.get("product_id") or product.get("product_id") or state.get("product_id", ""),
        "title": llm_output.get("title") or product.get("title", ""),
        "baseline_action": baseline_action,
        "baseline_confidence": baseline_confidence,
        "llm_final_action": llm_output.get("final_action", ""),
        "llm_confidence": llm_output.get("confidence", 0.0),
        "reasoning_summary": llm_output.get("reasoning_summary", ""),
        "key_risks": llm_output.get("key_risks", []),
        "key_opportunities": llm_output.get("key_opportunities", []),
        "caution_flags": llm_output.get("caution_flags", []),
        "follow_up_actions": llm_output.get("follow_up_actions", []),
        "supporting_evidence": llm_output.get("supporting_evidence", []),
    }

    return {"final_response": final_response}


def error_router(state: Dict[str, Any]) -> str:
    return "format_output" if state.get("error") else "reason_about_product"