from __future__ import annotations

import pandas as pd


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def confidence_from_margin(primary: float, secondary: float) -> float:
    margin = abs(primary - secondary)
    if margin >= 0.25:
        return 0.94
    if margin >= 0.16:
        return 0.86
    if margin >= 0.08:
        return 0.78
    return 0.70


def explain_row(row: pd.Series, action: str) -> str:
    parts = []

    if row["stockout_risk_score"] >= 0.72:
        parts.append("Stockout risk is high")
    elif row["stockout_risk_score"] >= 0.48:
        parts.append("Stockout risk is moderate")

    if row["overstock_risk_score"] >= 0.78:
        parts.append("Overstock risk is high")
    elif row["overstock_risk_score"] >= 0.58:
        parts.append("Overstock risk is moderate")

    if row["trend_strength_score"] >= 0.65:
        parts.append("Trend strength is strong")
    elif row["trend_strength_score"] <= 0.30:
        parts.append("Trend signal is weak")

    if row["demand_strength_score"] >= 0.60:
        parts.append("Demand strength is strong")
    elif row["demand_strength_score"] <= 0.30:
        parts.append("Demand strength is weak")

    if row["review_risk_score"] >= 0.70:
        parts.append("Customer quality/review risk is high")
    elif row["review_risk_score"] >= 0.45:
        parts.append("Customer review risk is moderate")

    if row["days_to_stockout"] > 0 and row["days_to_stockout"] < 999:
        parts.append(f"Estimated stockout in about {row['days_to_stockout']:.1f} days")

    if action == "RESTOCK_NOW":
        parts.append("Immediate replenishment is justified")
    elif action == "RESTOCK_CAUTIOUSLY":
        parts.append("Replenishment is justified but should be controlled")
    elif action == "CHECK_QUALITY_BEFORE_RESTOCK":
        parts.append("Quality should be reviewed before replenishment")
    elif action == "SLOW_REPLENISHMENT":
        parts.append("Replenishment should be slowed to reduce excess inventory")
    elif action == "HOLD":
        parts.append("Inventory should be held until signals improve")
    else:
        parts.append("Signals are mixed, so continued monitoring is recommended")

    return "; ".join(parts)


def get_category_profile(category_slug: str) -> dict:
    category_slug = (category_slug or "").strip().lower()

    if category_slug == "beauty_and_personal_care":
        return {
            "restock_bias": 0.95,
            "quality_bias": 1.20,
            "trend_bias": 0.90,
            "demand_bias": 0.95,
            "overstock_bias": 1.00,
        }

    if category_slug == "toys_and_games":
        return {
            "restock_bias": 1.12,
            "quality_bias": 0.95,
            "trend_bias": 1.20,
            "demand_bias": 1.00,
            "overstock_bias": 1.00,
        }

    return {
        "restock_bias": 1.00,
        "quality_bias": 1.00,
        "trend_bias": 0.92,
        "demand_bias": 1.10,
        "overstock_bias": 1.06,
    }


def decide_action(row: pd.Series) -> dict:
    stockout = float(row["stockout_risk_score"])
    overstock = float(row["overstock_risk_score"])
    review_risk = float(row["review_risk_score"])
    trend = float(row["trend_strength_score"])
    demand = float(row["demand_strength_score"])
    days_to_stockout = float(row["days_to_stockout"])
    category_slug = str(row.get("category_slug", "") or "")

    profile = get_category_profile(category_slug)

    urgency = 0.0
    if days_to_stockout < 999:
        urgency = clamp((35.0 - days_to_stockout) / 35.0)

    restock_now_score = profile["restock_bias"] * (
        0.44 * stockout
        + 0.20 * (demand * profile["demand_bias"])
        + 0.18 * (trend * profile["trend_bias"])
        + 0.10 * urgency
        + 0.08 * (1.0 - review_risk)
    )

    restock_cautious_score = profile["restock_bias"] * (
        0.34 * stockout
        + 0.22 * (demand * profile["demand_bias"])
        + 0.16 * (trend * profile["trend_bias"])
        + 0.10 * urgency
        + 0.10 * (1.0 - overstock)
        + 0.08 * (1.0 - review_risk)
    )

    quality_score = profile["quality_bias"] * (
        0.58 * review_risk
        + 0.16 * stockout
        + 0.14 * demand
        + 0.12 * trend
    )

    slow_score = profile["overstock_bias"] * (
        0.48 * overstock
        + 0.18 * (1.0 - trend)
        + 0.18 * (1.0 - demand)
        + 0.10 * review_risk
        + 0.06 * (1.0 - urgency)
    )

    hold_score = profile["overstock_bias"] * (
        0.56 * overstock
        + 0.22 * (1.0 - trend)
        + 0.16 * (1.0 - demand)
        + 0.06 * review_risk
    )

    monitor_score = (
        0.24
        + 0.18 * (1.0 - abs(stockout - 0.50))
        + 0.16 * (1.0 - abs(overstock - 0.50))
        + 0.16 * (1.0 - abs(demand - 0.50))
        + 0.10 * (1.0 - abs(trend - 0.45))
        + 0.16 * (1.0 - review_risk)
    )

    if stockout >= 0.58 or demand >= 0.58 or trend >= 0.62:
        monitor_score *= 0.72

    if overstock >= 0.72 and demand < 0.42 and trend < 0.42:
        monitor_score *= 0.65

    if review_risk < 0.45:
        quality_score *= 0.55

    if stockout < 0.35 and days_to_stockout > 42:
        restock_now_score *= 0.50
        restock_cautious_score *= 0.75

    if overstock < 0.45:
        slow_score *= 0.65
        hold_score *= 0.35

    if trend > 0.60 or demand > 0.60:
        hold_score *= 0.45

    if stockout > 0.62 and review_risk < 0.65:
        restock_now_score *= 1.12

    scores = {
        "RESTOCK_NOW": round(clamp(restock_now_score), 4),
        "RESTOCK_CAUTIOUSLY": round(clamp(restock_cautious_score), 4),
        "CHECK_QUALITY_BEFORE_RESTOCK": round(clamp(quality_score), 4),
        "SLOW_REPLENISHMENT": round(clamp(slow_score), 4),
        "HOLD": round(clamp(hold_score), 4),
        "MONITOR": round(clamp(monitor_score), 4),
    }

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    action, top_score = ranked[0]
    second_score = ranked[1][1]

    priority_map = {
        "RESTOCK_NOW": 1,
        "RESTOCK_CAUTIOUSLY": 2,
        "CHECK_QUALITY_BEFORE_RESTOCK": 3,
        "SLOW_REPLENISHMENT": 4,
        "HOLD": 5,
        "MONITOR": 6,
    }

    return {
        "action": action,
        "priority_rank": priority_map[action],
        "confidence": round(confidence_from_margin(top_score, second_score), 2),
        "evidence_summary": explain_row(row, action),
    }