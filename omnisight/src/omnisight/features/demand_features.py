from __future__ import annotations

import pandas as pd


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def safe_float(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def compute_days_to_stockout(current_inventory: float, weekly_units_sold: float) -> float:
    current_inventory = safe_float(current_inventory, 0.0)
    weekly_units_sold = safe_float(weekly_units_sold, 0.0)

    if current_inventory <= 0:
        return 0.0

    if weekly_units_sold <= 0:
        return 999.0

    # weekly_units_sold is per week, convert to days
    return round((current_inventory / weekly_units_sold) * 7.0, 2)


def score_stockout_risk(
    days_to_stockout: float,
    lead_time_days: float,
    weekly_units_sold: float,
    trend_change_pct: float,
) -> float:
    days_to_stockout = safe_float(days_to_stockout, 999.0)
    lead_time_days = safe_float(lead_time_days, 0.0)
    weekly_units_sold = safe_float(weekly_units_sold, 0.0)
    trend_change_pct = safe_float(trend_change_pct, 0.0)

    days_score = (
        1.0 if days_to_stockout <= 7
        else 0.8 if days_to_stockout <= 14
        else 0.5 if days_to_stockout <= 30
        else 0.2
    )

    lead_time_pressure = (
        1.0 if lead_time_days >= days_to_stockout
        else 0.7 if lead_time_days >= days_to_stockout * 0.7
        else 0.3
    )

    demand_pressure = (
        1.0 if weekly_units_sold >= 100
        else 0.7 if weekly_units_sold >= 50
        else 0.4 if weekly_units_sold >= 20
        else 0.2
    )

    trend_boost = (
        1.0 if trend_change_pct >= 25
        else 0.7 if trend_change_pct >= 10
        else 0.4 if trend_change_pct > 0
        else 0.2
    )

    score = (0.4 * days_score) + (0.25 * lead_time_pressure) + (0.2 * demand_pressure) + (0.15 * trend_boost)
    return round(clamp(score), 4)


def score_overstock_risk(current_inventory: float, weekly_units_sold: float, trend_change_pct: float) -> float:
    current_inventory = safe_float(current_inventory, 0.0)
    weekly_units_sold = safe_float(weekly_units_sold, 1.0)
    trend_change_pct = safe_float(trend_change_pct, 0.0)

    cover_weeks = current_inventory / max(weekly_units_sold, 1.0)

    cover_score = (
        1.0 if cover_weeks >= 10
        else 0.8 if cover_weeks >= 7
        else 0.5 if cover_weeks >= 4
        else 0.2
    )

    weak_trend_score = (
        1.0 if trend_change_pct <= -20
        else 0.8 if trend_change_pct <= -5
        else 0.5 if trend_change_pct <= 5
        else 0.2
    )

    score = (0.7 * cover_score) + (0.3 * weak_trend_score)
    return round(clamp(score), 4)


def score_review_risk(avg_rating: float, review_count: float) -> float:
    avg_rating = safe_float(avg_rating, 0.0)
    review_count = safe_float(review_count, 0.0)

    if review_count == 0:
        return 0.4

    rating_score = (
        1.0 if avg_rating <= 2.5
        else 0.8 if avg_rating <= 3.2
        else 0.5 if avg_rating <= 3.8
        else 0.2
    )

    confidence_boost = (
        1.0 if review_count >= 20
        else 0.8 if review_count >= 10
        else 0.6 if review_count >= 5
        else 0.4
    )

    score = rating_score * confidence_boost
    return round(clamp(score), 4)


def score_trend_strength(latest_trend_index: float, avg_trend_change_pct: float, trend_points: float) -> float:
    latest_trend_index = safe_float(latest_trend_index, 0.0)
    avg_trend_change_pct = safe_float(avg_trend_change_pct, 0.0)
    trend_points = safe_float(trend_points, 0.0)

    level_score = (
        1.0 if latest_trend_index >= 80
        else 0.8 if latest_trend_index >= 60
        else 0.5 if latest_trend_index >= 30
        else 0.2
    )

    growth_score = (
        1.0 if avg_trend_change_pct >= 25
        else 0.8 if avg_trend_change_pct >= 10
        else 0.5 if avg_trend_change_pct > 0
        else 0.2
    )

    coverage_score = (
        1.0 if trend_points >= 8
        else 0.7 if trend_points >= 4
        else 0.4 if trend_points > 0
        else 0.1
    )

    score = (0.45 * level_score) + (0.35 * growth_score) + (0.2 * coverage_score)
    return round(clamp(score), 4)


def score_demand_strength(weekly_units_sold: float, review_count: float, latest_trend_index: float) -> float:
    weekly_units_sold = safe_float(weekly_units_sold, 0.0)
    review_count = safe_float(review_count, 0.0)
    latest_trend_index = safe_float(latest_trend_index, 0.0)

    velocity_score = (
        1.0 if weekly_units_sold >= 100
        else 0.8 if weekly_units_sold >= 50
        else 0.5 if weekly_units_sold >= 20
        else 0.2
    )

    social_proof_score = (
        1.0 if review_count >= 50
        else 0.8 if review_count >= 20
        else 0.5 if review_count >= 5
        else 0.2
    )

    trend_score = (
        1.0 if latest_trend_index >= 80
        else 0.8 if latest_trend_index >= 60
        else 0.5 if latest_trend_index >= 30
        else 0.2
    )

    score = (0.5 * velocity_score) + (0.2 * social_proof_score) + (0.3 * trend_score)
    return round(clamp(score), 4)


def build_decision_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    numeric_cols = [
        "current_inventory",
        "weekly_units_sold",
        "lead_time_days",
        "review_count",
        "avg_rating",
        "avg_helpfulness",
        "latest_trend_index",
        "avg_trend_change_pct",
        "trend_points",
    ]

    for col in numeric_cols:
        if col not in out.columns:
            out[col] = 0
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)

    # IMPORTANT: compute this instead of defaulting it to 0
    out["days_to_stockout"] = out.apply(
        lambda row: compute_days_to_stockout(
            row["current_inventory"],
            row["weekly_units_sold"],
        ),
        axis=1,
    )

    out["stockout_risk_score"] = out.apply(
        lambda row: score_stockout_risk(
            row["days_to_stockout"],
            row["lead_time_days"],
            row["weekly_units_sold"],
            row["avg_trend_change_pct"],
        ),
        axis=1,
    )

    out["overstock_risk_score"] = out.apply(
        lambda row: score_overstock_risk(
            row["current_inventory"],
            row["weekly_units_sold"],
            row["avg_trend_change_pct"],
        ),
        axis=1,
    )

    out["review_risk_score"] = out.apply(
        lambda row: score_review_risk(
            row["avg_rating"],
            row["review_count"],
        ),
        axis=1,
    )

    out["trend_strength_score"] = out.apply(
        lambda row: score_trend_strength(
            row["latest_trend_index"],
            row["avg_trend_change_pct"],
            row["trend_points"],
        ),
        axis=1,
    )

    out["demand_strength_score"] = out.apply(
        lambda row: score_demand_strength(
            row["weekly_units_sold"],
            row["review_count"],
            row["latest_trend_index"],
        ),
        axis=1,
    )

    out["inventory_cover_weeks"] = (
        out["current_inventory"] / out["weekly_units_sold"].replace(0, 1)
    ).round(2)

    out["lead_time_vs_stockout_ratio"] = (
        out["lead_time_days"] / out["days_to_stockout"].replace(0, 1)
    ).round(2)

    return out