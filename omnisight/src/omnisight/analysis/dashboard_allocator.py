from __future__ import annotations

import pandas as pd


def allocate_dashboard_and_monitoring(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    def priority_value(row) -> int:
        stock_flag = str(row.get("stock_flag", "") or "")
        trend = str(row.get("trend_classification", "") or "")
        qty = float(row.get("current_quantity", 0.0) or 0.0)
        weekly = float(row.get("projected_weekly_demand", 0.0) or 0.0)

        weeks_cover = qty / max(weekly, 1.0)

        if stock_flag == "CRITICAL":
            return 4
        if stock_flag == "LOW STOCK":
            return 3
        if stock_flag == "OVERSTOCK":
            return 2
        if trend == "Trending Up" and weeks_cover <= 4.0:
            return 2
        if trend == "Trending Down" and weeks_cover >= 6.0:
            return 1
        return 0

    out["dashboard_priority"] = out.apply(priority_value, axis=1)

    out = out.sort_values(
        by=["dashboard_priority", "urgency_rank_score", "confidence_pct"],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    out["destination_view"] = "monitoring"

    top_n = min(5, len(out))
    if top_n > 0:
        out.loc[: top_n - 1, "destination_view"] = "dashboard"

    return out