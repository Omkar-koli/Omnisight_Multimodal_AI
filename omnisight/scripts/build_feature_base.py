from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MERGED_DIR = PROJECT_ROOT / "data" / "processed" / "merged"

PRODUCTS = MERGED_DIR / "products_current.parquet"
REVIEWS = MERGED_DIR / "reviews_current.parquet"
TRENDS = MERGED_DIR / "trends_current.parquet"

OUTPUT = MERGED_DIR / "feature_base.parquet"


def pick_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    return None


def add_missing_columns(df: pd.DataFrame, columns: dict[str, object]) -> pd.DataFrame:
    df = df.copy()
    for col, default in columns.items():
        if col not in df.columns:
            df[col] = default
    return df


def main() -> None:
    if not PRODUCTS.exists():
        raise FileNotFoundError(f"Missing {PRODUCTS}")

    products_df = pd.read_parquet(PRODUCTS).copy()
    products_df["product_id"] = products_df["product_id"].astype("string")

    products_df = add_missing_columns(
        products_df,
        {
            "category_slug": "",
            "category_label": "",
            "category": "",
        },
    )

    # -------------------------
    # Reviews summary
    # -------------------------
    if REVIEWS.exists():
        reviews_df = pd.read_parquet(REVIEWS).copy()
        reviews_df["product_id"] = reviews_df["product_id"].astype("string")

        helpful_col = pick_existing_column(reviews_df, ["helpful_vote", "helpfulness"])
        if helpful_col is None:
            reviews_df["helpful_metric"] = 0.0
        else:
            reviews_df["helpful_metric"] = pd.to_numeric(
                reviews_df[helpful_col], errors="coerce"
            ).fillna(0.0)

        if "rating" not in reviews_df.columns:
            reviews_df["rating"] = 0.0
        reviews_df["rating"] = pd.to_numeric(reviews_df["rating"], errors="coerce").fillna(0.0)

        review_summary = (
            reviews_df.groupby("product_id", dropna=False)
            .agg(
                review_count=("product_id", "count"),
                avg_rating=("rating", "mean"),
                avg_helpfulness=("helpful_metric", "mean"),
            )
            .reset_index()
        )
    else:
        review_summary = pd.DataFrame(
            columns=["product_id", "review_count", "avg_rating", "avg_helpfulness"]
        )

    # -------------------------
    # Trends summary
    # -------------------------
    if TRENDS.exists():
        trends_df = pd.read_parquet(TRENDS).copy()
        trends_df["product_id"] = trends_df["product_id"].astype("string")
        trends_df = trends_df[trends_df["product_id"].notna()].copy()

        if "trend_index" not in trends_df.columns:
            trends_df["trend_index"] = 0.0
        if "trend_change_pct" not in trends_df.columns:
            trends_df["trend_change_pct"] = 0.0

        trends_df["trend_index"] = pd.to_numeric(trends_df["trend_index"], errors="coerce").fillna(0.0)
        trends_df["trend_change_pct"] = pd.to_numeric(
            trends_df["trend_change_pct"], errors="coerce"
        ).fillna(0.0)

        sort_col = None
        if "captured_at" in trends_df.columns:
            trends_df["_trend_ts"] = pd.to_datetime(
                trends_df["captured_at"], errors="coerce", utc=True
            )
            sort_col = "_trend_ts"
        elif "week" in trends_df.columns:
            trends_df["_trend_ts"] = pd.to_datetime(
                trends_df["week"], errors="coerce", utc=True
            )
            sort_col = "_trend_ts"

        if sort_col is not None:
            trends_df = trends_df.sort_values(
                ["product_id", sort_col], ascending=[True, True]
            )

        trends_summary = (
            trends_df.groupby("product_id", dropna=False)
            .agg(
                latest_trend_index=("trend_index", "last"),
                avg_trend_change_pct=("trend_change_pct", "mean"),
                trend_points=("trend_index", "count"),
            )
            .reset_index()
        )
    else:
        trends_summary = pd.DataFrame(
            columns=["product_id", "latest_trend_index", "avg_trend_change_pct", "trend_points"]
        )

    if not review_summary.empty:
        review_summary["product_id"] = review_summary["product_id"].astype("string")
    else:
        review_summary["product_id"] = pd.Series(dtype="string")

    if not trends_summary.empty:
        trends_summary["product_id"] = trends_summary["product_id"].astype("string")
    else:
        trends_summary["product_id"] = pd.Series(dtype="string")

    # -------------------------
    # Merge into feature base
    # -------------------------
    base = products_df.merge(review_summary, on="product_id", how="left")
    base = base.merge(trends_summary, on="product_id", how="left")

    base["review_count"] = base["review_count"].fillna(0).astype(int)
    base["avg_rating"] = base["avg_rating"].fillna(0.0)
    base["avg_helpfulness"] = base["avg_helpfulness"].fillna(0.0)
    base["latest_trend_index"] = base["latest_trend_index"].fillna(0.0)
    base["avg_trend_change_pct"] = base["avg_trend_change_pct"].fillna(0.0)
    base["trend_points"] = base["trend_points"].fillna(0).astype(int)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    base.to_parquet(OUTPUT, index=False)

    print(f"Saved {OUTPUT}")
    print(base.head())
    print("\nCategory counts:")
    if "category_slug" in base.columns:
        print(base["category_slug"].value_counts(dropna=False))


if __name__ == "__main__":
    main()