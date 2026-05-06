from __future__ import annotations

from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RECOMMENDATIONS_PATH = PROCESSED_DIR / "recommendations.parquet"


def main() -> None:
    if not RECOMMENDATIONS_PATH.exists():
        raise FileNotFoundError("Missing recommendations.parquet. Run 11_run_decision_engine.py first.")

    df = pd.read_parquet(RECOMMENDATIONS_PATH)

    query = input("Enter product title keyword or product_id: ").strip().lower()

    if not query:
        print("No query entered.")
        return

    matches = df[
        df["product_id"].astype(str).str.lower().str.contains(query, na=False)
        | df["title"].astype(str).str.lower().str.contains(query, na=False)
    ].copy()

    if matches.empty:
        print("No matching products found.")
        return

    cols = [
        "product_id",
        "title",
        "category",
        "current_inventory",
        "weekly_units_sold",
        "days_to_stockout",
        "stockout_risk_score",
        "overstock_risk_score",
        "review_risk_score",
        "trend_strength_score",
        "action",
        "confidence",
        "evidence_summary",
    ]
    cols = [c for c in cols if c in matches.columns]

    print(matches[cols].head(10).to_string(index=False))


if __name__ == "__main__":
    main()