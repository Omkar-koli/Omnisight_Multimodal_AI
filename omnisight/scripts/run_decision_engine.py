from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from omnisight.analysis.dashboard_allocator import allocate_dashboard_and_monitoring
from omnisight.analysis.product_analyzer import analyze_product

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MERGED_DIR = PROJECT_ROOT / "data" / "processed" / "merged"

INPUT_PATH = MERGED_DIR / "decision_features.parquet"
OUTPUT_PATH = MERGED_DIR / "recommendations.parquet"
PREVIEW_PATH = MERGED_DIR / "recommendations_preview.csv"

DASHBOARD_TOP5_PATH = MERGED_DIR / "dashboard_top5.parquet"
MONITORING_PRODUCTS_PATH = MERGED_DIR / "monitoring_products.parquet"


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Missing {INPUT_PATH}. Run your decision-features build step first."
        )

    df = pd.read_parquet(INPUT_PATH).copy()

    analyses = []
    for _, row in df.iterrows():
        analyses.append(asdict(analyze_product(row.to_dict())))

    out = pd.DataFrame(analyses)

    if out.empty:
        raise ValueError("No product analyses were generated from decision_features.parquet")

    out = allocate_dashboard_and_monitoring(out)

    sort_cols = [
        "destination_view",
        "dashboard_priority",
        "urgency_rank_score",
        "confidence_pct",
        "stock_flag",
        "trend_classification",
    ]
    existing_sort_cols = [c for c in sort_cols if c in out.columns]

    if existing_sort_cols:
        ascending = []
        for col in existing_sort_cols:
            if col in {"destination_view"}:
                ascending.append(True)
            elif col in {"stock_flag", "trend_classification"}:
                ascending.append(True)
            else:
                ascending.append(False)

        out = out.sort_values(
            by=existing_sort_cols,
            ascending=ascending,
        ).reset_index(drop=True)

    MERGED_DIR.mkdir(parents=True, exist_ok=True)

    out.to_parquet(OUTPUT_PATH, index=False)
    out.to_csv(PREVIEW_PATH, index=False)

    dashboard_df = out[out["destination_view"] == "dashboard"].copy()
    monitoring_df = out[out["destination_view"] == "monitoring"].copy()

    dashboard_df.to_parquet(DASHBOARD_TOP5_PATH, index=False)
    monitoring_df.to_parquet(MONITORING_PRODUCTS_PATH, index=False)

    preview_cols = [
        "product_id",
        "title",
        "category_slug",
        "category_label",
        "stock_flag",
        "current_quantity",
        "trend_classification",
        "projected_weekly_demand",
        "threshold_units",
        "recommended_order_qty",
        "confidence_pct",
        "manual_review_required",
        "destination_view",
        "executive_summary",
    ]
    existing_preview_cols = [c for c in preview_cols if c in out.columns]

    print(f"Saved recommendations to      : {OUTPUT_PATH}")
    print(f"Saved preview to              : {PREVIEW_PATH}")
    print(f"Saved dashboard top 5 to      : {DASHBOARD_TOP5_PATH}")
    print(f"Saved monitoring products to  : {MONITORING_PRODUCTS_PATH}")
    print()
    print(out[existing_preview_cols].head(15).to_string(index=False))

    if "category_slug" in out.columns:
        print("\nCategory counts:")
        print(out["category_slug"].value_counts(dropna=False))

    if "destination_view" in out.columns:
        print("\nDestination counts:")
        print(out["destination_view"].value_counts(dropna=False))

    if "stock_flag" in out.columns:
        print("\nStock flag counts:")
        print(out["stock_flag"].value_counts(dropna=False))


if __name__ == "__main__":
    main()