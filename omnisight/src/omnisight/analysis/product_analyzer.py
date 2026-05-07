from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from omnisight.analysis.types import ProductAnalysis


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default

def normalize_sequence(value: Any) -> list[float]:
    if value is None:
        return []

    if isinstance(value, list):
        return [safe_float(v) for v in value]

    if isinstance(value, tuple):
        return [safe_float(v) for v in value]

    # handles numpy arrays / pandas arrays / series-like values
    if hasattr(value, "tolist"):
        raw = value.tolist()
        if isinstance(raw, list):
            return [safe_float(v) for v in raw]
        return [safe_float(raw)]

    return [safe_float(value)]

def recent_avg(values: list[float], n: int) -> float:
    vals = [safe_float(v) for v in values if v is not None]
    if not vals:
        return 0.0
    vals = vals[-n:]
    return sum(vals) / len(vals)

def normalize_text_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]

    if isinstance(value, tuple):
        return [str(v).strip() for v in value if str(v).strip()]

    if hasattr(value, "tolist"):
        raw = value.tolist()
        if isinstance(raw, list):
            return [str(v).strip() for v in raw if str(v).strip()]
        raw = str(raw).strip()
        return [raw] if raw else []

    text = str(value).strip()
    return [text] if text else []

def first_nonempty_text_list(row: Dict[str, Any], candidate_keys: list[str]) -> list[str]:
    for key in candidate_keys:
        values = normalize_text_list(row.get(key))
        if len(values) > 0:
            return values
    return []

def dedupe_keep_order(values: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(value.strip())
    return out


def build_trending_reason_block(
    row: Dict[str, Any],
    trend_classification: str,
    recent_review_avg: float,
    older_review_avg: float,
    recent_review_count: int,
    older_review_count: int,
) -> tuple[list[str], list[str], str]:
    """
    Returns:
      trend_keywords,
      trend_reasons,
      trend_reason_confidence
    """

    if trend_classification != "Trending Up":
        return [], [], "not_applicable"

    trend_keywords = first_nonempty_text_list(
    row,
    [
        "trend_search_keywords",
        "related_queries_top",
        "google_trends_keywords",
        "trend_keywords",
    ],
)

    review_terms = first_nonempty_text_list(
    row,
    [
        "recent_review_keywords_30d",
        "recent_review_title_keywords",
        "recent_review_phrases_30d",
    ],
)

    review_titles = first_nonempty_text_list(
    row,
    [
        "recent_review_titles_30d",
        "recent_review_headlines_30d",
    ],
)

    keywords = dedupe_keep_order(trend_keywords + review_terms)
    keywords = keywords[:5]

    reasons: list[str] = []

    if keywords:
        reasons.append(
            f"Search interest is being driven by terms such as {', '.join(keywords[:3])}."
        )

    if recent_review_count >= 3 and review_terms:
        reasons.append(
            f"Recent reviews repeatedly mention {', '.join(review_terms[:3])}, which aligns with the current demand lift."
        )
    elif recent_review_count >= 3 and review_titles:
        reasons.append(
            "Recent review titles show repeated buyer interest in the same product benefits over the last 30 days."
        )

    if recent_review_avg >= older_review_avg + 0.18:
        reasons.append(
            "Review sentiment improved versus the prior period, suggesting stronger current buyer response."
        )

    if recent_review_count > older_review_count and recent_review_count >= 3:
        reasons.append(
            "Review activity is higher in the last 30 days than the earlier period, indicating more recent attention."
        )

    reasons = dedupe_keep_order(reasons)[:3]

    if recent_review_count < 3 and len(keywords) < 2:
        confidence = "low"
        if not reasons:
            reasons = [
                "Recent reviews are too few or too old to explain the trend reliably."
            ]
    elif recent_review_count < 5 or len(keywords) < 3:
        confidence = "moderate"
    else:
        confidence = "high"

    return keywords, reasons, confidence

def classify_trend(
    trend_values: list[float],
    recent_review_avg: float,
    older_review_avg: float,
    recent_review_count: int,
    older_review_count: int,
) -> tuple[str, bool, str]:
    recent_trend = recent_avg(trend_values, 4)
    long_trend = recent_avg(trend_values, 12)

    trend_delta = 0.0
    if long_trend > 0:
        trend_delta = (recent_trend - long_trend) / long_trend

    review_delta = recent_review_avg - older_review_avg

    trend_up = trend_delta >= 0.12
    trend_down = trend_delta <= -0.12
    reviews_up = review_delta >= 0.18
    reviews_down = review_delta <= -0.18

    if trend_up and reviews_down:
        return (
            "Trending Up",
            True,
            "Search interest is rising, but recent reviews are weakening. Momentum is positive, but buyer experience is a caution flag.",
        )

    if trend_down and reviews_up:
        return (
            "Stable",
            True,
            "Search interest is weakening, but recent reviews are improving. Signals conflict, so the trend is treated cautiously.",
        )

    if trend_up or reviews_up:
        return (
            "Trending Up",
            False,
            "Recent search and/or review signals indicate upward momentum.",
        )

    if trend_down or reviews_down:
        return (
            "Trending Down",
            False,
            "Recent search and/or review signals indicate weakening momentum.",
        )

    return (
        "Stable",
        False,
        "Search and review signals do not show a strong directional shift.",
    )


def compute_dynamic_threshold(
    weekly_sales_history: list[float],
    stockout_count_90d: int,
    trend_classification: str,
    lead_time_weeks: float,
) -> tuple[float, float, str]:
    last_4 = recent_avg(weekly_sales_history, 4)
    last_12 = recent_avg(weekly_sales_history, 12)

    if last_12 <= 0:
        base_pace = max(last_4, 1.0)
        reason = "Used recent pace because longer sales history was weak or unavailable."
    else:
        change_pct = abs(last_4 - last_12) / last_12
        if change_pct > 0.15:
            base_pace = max(last_4, 1.0)
            reason = "Used recent 4-week sales pace because it differs materially from the 12-week baseline."
        else:
            base_pace = max(last_12, 1.0)
            reason = "Used 12-week average pace because recent sales do not differ enough to justify overriding it."


    safety_weeks = 1.25
    if stockout_count_90d > 0:
        safety_weeks += min(stockout_count_90d * 0.25, 0.75)

    if trend_classification == "Trending Up":
        safety_weeks += 0.5
    elif trend_classification == "Trending Down":
        safety_weeks -= 0.25

    safety_weeks = max(1.0, safety_weeks)

    threshold = base_pace * (lead_time_weeks + safety_weeks)

    explanation = (
        f"{reason} Threshold uses demand pace ({base_pace:.2f} units/week) "
        f"times lead time ({lead_time_weeks:.1f} weeks) plus safety buffer "
        f"({safety_weeks:.1f} weeks)."
    )

    return round(threshold, 2), round(base_pace, 2), explanation


def flag_stock(
    current_quantity: float,
    threshold_units: float,
    trend_classification: str,
    projected_weekly_demand: float,
) -> tuple[str, float]:
    ratio = current_quantity / max(threshold_units, 1.0)
    weeks_cover = current_quantity / max(projected_weekly_demand, 1.0)

    if current_quantity < threshold_units * 0.45:
        return "CRITICAL", round(threshold_units - current_quantity, 2)

    if current_quantity < threshold_units * 0.90:
        return "LOW STOCK", round(threshold_units - current_quantity, 2)

    if (
        (trend_classification == "Trending Down" and ratio >= 1.35)
        or ratio >= 1.75
        or weeks_cover >= 8.0
    ):
        return "OVERSTOCK", round(current_quantity - threshold_units, 2)

    return "SUFFICIENT", 0.0


def recommend_order(
    stock_flag: str,
    trend_classification: str,
    current_quantity: float,
    projected_weekly_demand: float,
    lead_time_weeks: float,
    stockout_count_90d: int,
) -> tuple[float, str]:
    if stock_flag in {"LOW STOCK", "CRITICAL"} or trend_classification == "Trending Up":
        safety_weeks = 3.0 if stockout_count_90d > 0 else 2.0
        needed = projected_weekly_demand * (lead_time_weeks + safety_weeks)

        if trend_classification == "Trending Up":
            needed *= 1.15

        order_qty = max(0.0, needed - current_quantity)
        explanation = (
            f"At roughly {projected_weekly_demand:.2f} units/week and about {lead_time_weeks:.1f} weeks lead time, "
            f"the business should cover lead time plus a {int(safety_weeks)}-week safety buffer."
        )
        return round(order_qty, 2), explanation

    if stock_flag == "OVERSTOCK":
        weeks_cover = current_quantity / max(projected_weekly_demand, 1.0)
        explanation = (
            f"Do not reorder. Inventory is above threshold and current stock covers about {weeks_cover:.1f} weeks. "
            f"Because demand/trend is soft, replenishment should be slowed until stock normalizes."
        )
        return 0.0, explanation

    weeks_cover = current_quantity / max(projected_weekly_demand, 1.0)
    explanation = (
        f"Do not reorder now. Current stock should last about {weeks_cover:.1f} weeks at the current demand pace. "
        f"Watch for a demand increase, stockouts, or a stronger upward trend before reconsidering."
    )
    return 0.0, explanation


def compute_confidence(
    trend_conflict: bool,
    has_sales_history: bool,
    trend_points: int,
    review_points: int,
    stock_flag: str,
    recommended_order_qty: float,
    trend_classification: str,
) -> tuple[float, str, bool]:
    confidence = 78.0
    notes: list[str] = []

    if not has_sales_history:
        confidence -= 8
        notes.append("Limited sales history reduced confidence.")

    if trend_points < 6:
        confidence -= 5
        notes.append("Trend data is somewhat sparse.")

    if review_points < 5:
        confidence -= 5
        notes.append("Review volume is limited.")

    if trend_conflict:
        confidence -= 8
        notes.append("Trend and review signals conflict.")

    if stock_flag == "CRITICAL":
        confidence += 8
        notes.append("Current stock is clearly critical.")
    elif stock_flag == "LOW STOCK":
        confidence += 5
        notes.append("Current stock is below threshold.")

    if recommended_order_qty > 0:
        confidence += 4
        notes.append("Order recommendation is supported by stock position and demand pace.")

    if trend_classification == "Trending Up":
        confidence += 3
        notes.append("Trend direction supports urgency.")
    elif trend_classification == "Trending Down":
        confidence += 3
        notes.append("Trend direction supports caution.")

    confidence = max(50.0, min(90.0, confidence))
    manual_review_required = confidence < 35.0

    if not notes:
        notes.append("Signals are reasonably aligned.")

    return round(confidence, 1), " ".join(notes), manual_review_required


def build_executive_summary(
    stock_flag: str,
    current_quantity: float,
    trend_classification: str,
    recommended_order_qty: float,
    confidence_pct: float,
    caveat: str,
) -> str:
    if recommended_order_qty > 0:
        action_text = f"Recommend ordering about {recommended_order_qty:.0f} units."
    else:
        action_text = "Do not restock yet."

    return (
        f"{stock_flag}: current stock is {current_quantity:.0f} units. "
        f"Trend classification is {trend_classification}. "
        f"{action_text} "
        f"Confidence is {confidence_pct:.1f}%. "
        f"Key caveat: {caveat}"
    )


def analyze_product(row: Dict[str, Any]) -> ProductAnalysis:
    weekly_sales_history = normalize_sequence(row.get("weekly_sales_history", []))
    trend_values = normalize_sequence(row.get("trend_values", []))

    recent_review_avg = safe_float(row.get("recent_review_avg", 0.0))
    older_review_avg = safe_float(row.get("older_review_avg", 0.0))
    recent_review_count = int(safe_float(row.get("recent_review_count", 0)))
    older_review_count = int(safe_float(row.get("older_review_count", 0)))
    stockout_count_90d = int(safe_float(row.get("stockout_count_90d", 0)))

    current_quantity = safe_float(row.get("current_inventory", 0.0))
    lead_time_weeks = max(1.0, safe_float(row.get("lead_time_days", 7.0)) / 7.0)

    trend_classification, trend_conflict, trend_summary = classify_trend(
        trend_values=trend_values,
        recent_review_avg=recent_review_avg,
        older_review_avg=older_review_avg,
        recent_review_count=recent_review_count,
        older_review_count=older_review_count,
    )

    threshold_units, projected_weekly_demand, threshold_explanation = compute_dynamic_threshold(
    weekly_sales_history=weekly_sales_history,
    stockout_count_90d=stockout_count_90d,
    trend_classification=trend_classification,
    lead_time_weeks=lead_time_weeks,
    )

    stock_flag, units_short = flag_stock(
    current_quantity=current_quantity,
    threshold_units=threshold_units,
    trend_classification=trend_classification,
    projected_weekly_demand=projected_weekly_demand,
)

    recommended_order_qty, order_recommendation = recommend_order(
        stock_flag=stock_flag,
        trend_classification=trend_classification,
        current_quantity=current_quantity,
        projected_weekly_demand=projected_weekly_demand,
        lead_time_weeks=lead_time_weeks,
        stockout_count_90d=stockout_count_90d,
    )

    confidence_pct, confidence_notes, manual_review_required = compute_confidence(
    trend_conflict=trend_conflict,
    has_sales_history=len(weekly_sales_history) > 0,
    trend_points=len(trend_values),
    review_points=recent_review_count + older_review_count,
    stock_flag=stock_flag,
    recommended_order_qty=recommended_order_qty,
    trend_classification=trend_classification,
    )
    trend_keywords, trend_reasons, trend_reason_confidence = build_trending_reason_block(
        row=row,
        trend_classification=trend_classification,
        recent_review_avg=recent_review_avg,
        older_review_avg=older_review_avg,
        recent_review_count=recent_review_count,
        older_review_count=older_review_count,
    )
    

    urgency_rank_score = 0.0
    if stock_flag == "CRITICAL":
        urgency_rank_score = 300 + confidence_pct
    elif stock_flag == "LOW STOCK":
        urgency_rank_score = 220 + confidence_pct
    elif stock_flag == "OVERSTOCK":
        urgency_rank_score = 180 + confidence_pct
    else:
        weeks_left = current_quantity / max(projected_weekly_demand, 1.0)
        if trend_classification == "Trending Up" and weeks_left <= 2.5:
            urgency_rank_score = 140 + confidence_pct
        elif trend_classification == "Trending Down" and weeks_left >= 6.0:
            urgency_rank_score = 120 + confidence_pct
        else:
            urgency_rank_score = 60 + (confidence_pct / 10.0)

    executive_summary = build_executive_summary(
        stock_flag=stock_flag,
        current_quantity=current_quantity,
        trend_classification=trend_classification,
        recommended_order_qty=recommended_order_qty,
        confidence_pct=confidence_pct,
        caveat=confidence_notes,
    )
    

    return ProductAnalysis(
        product_id=str(row.get("product_id", "")),
        title=str(row.get("title", "")),
        category_slug=str(row.get("category_slug", "")),
        category_label=str(row.get("category_label", "")),
        trend_classification=trend_classification,
        trend_conflict=trend_conflict,
        trend_summary=trend_summary,
        projected_weekly_demand=projected_weekly_demand,
        threshold_units=threshold_units,
        threshold_explanation=threshold_explanation,
        current_quantity=current_quantity,
        stock_flag=stock_flag,
        units_short=units_short,
        recommended_order_qty=recommended_order_qty,
        order_recommendation=order_recommendation,
        confidence_pct=confidence_pct,
        confidence_notes=confidence_notes,
        manual_review_required=manual_review_required,
        executive_summary=executive_summary,
        urgency_rank_score=urgency_rank_score,
        destination_view="monitoring",
        trend_keywords=trend_keywords,
        trend_reasons=trend_reasons,
        trend_reason_confidence=trend_reason_confidence,
    )