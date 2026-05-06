from __future__ import annotations

from pathlib import Path
import math
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PRODUCTS_PATH = PROCESSED_DIR / "products.parquet"
FEATURE_BASE_PATH = PROCESSED_DIR / "feature_base.parquet"
INVENTORY_SEED_PATH = RAW_DIR / "inventory_seed.csv"
OUTPUT_PATH = PROCESSED_DIR / "inventory.parquet"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def build_seed_inventory(products_df: pd.DataFrame, feature_base_df: pd.DataFrame) -> pd.DataFrame:
    df = products_df[["product_id", "title", "category"]].copy()
    df["product_id"] = df["product_id"].astype("string")

    if not feature_base_df.empty:
        feature_base_df["product_id"] = feature_base_df["product_id"].astype("string")
        keep_cols = [c for c in ["product_id", "review_count", "avg_rating", "latest_trend_index", "avg_trend_change_pct"] if c in feature_base_df.columns]
        df = df.merge(feature_base_df[keep_cols], on="product_id", how="left")
    else:
        df["review_count"] = 0
        df["avg_rating"] = 0
        df["latest_trend_index"] = 0
        df["avg_trend_change_pct"] = 0

    df["review_count"] = pd.to_numeric(df.get("review_count", 0), errors="coerce").fillna(0)
    df["avg_rating"] = pd.to_numeric(df.get("avg_rating", 0), errors="coerce").fillna(0)
    df["latest_trend_index"] = pd.to_numeric(df.get("latest_trend_index", 0), errors="coerce").fillna(0)
    df["avg_trend_change_pct"] = pd.to_numeric(df.get("avg_trend_change_pct", 0), errors="coerce").fillna(0)

    # Deterministic weekly sales estimate from available signals
    df["weekly_units_sold"] = (
        8
        + (df["review_count"] * 0.6)
        + (df["latest_trend_index"] * 0.25)
        + (df["avg_trend_change_pct"].clip(lower=0) * 0.35)
    ).round().astype(int)

    df["weekly_units_sold"] = df["weekly_units_sold"].clip(lower=5, upper=150)

    # Lead time based loosely on category
    def lead_time_from_category(cat: str) -> int:
        cat = str(cat).lower()
        if "beauty" in cat or "grocery" in cat:
            return 7
        if "electronics" in cat:
            return 14
        if "home" in cat:
            return 10
        if "clothing" in cat or "jewelry" in cat:
            return 9
        return 12

    df["lead_time_days"] = df["category"].apply(lead_time_from_category)

    # Inventory target: around 2 to 6 weeks of cover depending on sales/trend
    cover_weeks = (
        2.5
        + (1 - (df["avg_trend_change_pct"].clip(lower=0, upper=40) / 40.0)) * 2
    )
    cover_weeks = cover_weeks.clip(lower=2.0, upper=6.0)

    df["current_inventory"] = (df["weekly_units_sold"] * cover_weeks).round().astype(int)
    df["current_inventory"] = df["current_inventory"].clip(lower=20)

    df["supplier"] = "default_supplier"
    df["min_order_qty"] = 24

    seed_df = df[[
        "product_id",
        "current_inventory",
        "weekly_units_sold",
        "lead_time_days",
        "supplier",
        "min_order_qty",
    ]].copy()

    return seed_df


def main() -> None:
    if not PRODUCTS_PATH.exists():
        raise FileNotFoundError("Missing data/processed/products.parquet")

    products_df = pd.read_parquet(PRODUCTS_PATH)

    if FEATURE_BASE_PATH.exists():
        feature_base_df = pd.read_parquet(FEATURE_BASE_PATH)
    else:
        feature_base_df = pd.DataFrame()

    # If no seed CSV exists yet, generate one automatically
    if not INVENTORY_SEED_PATH.exists():
        seed_df = build_seed_inventory(products_df, feature_base_df)
        INVENTORY_SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
        seed_df.to_csv(INVENTORY_SEED_PATH, index=False)
        print(f"Created starter inventory seed file: {INVENTORY_SEED_PATH}")

    inventory_df = pd.read_csv(INVENTORY_SEED_PATH)
    inventory_df["product_id"] = inventory_df["product_id"].astype("string")
    inventory_df["current_inventory"] = pd.to_numeric(inventory_df["current_inventory"], errors="coerce").fillna(0)
    inventory_df["weekly_units_sold"] = pd.to_numeric(inventory_df["weekly_units_sold"], errors="coerce").fillna(1)
    inventory_df["lead_time_days"] = pd.to_numeric(inventory_df["lead_time_days"], errors="coerce").fillna(7)
    inventory_df["min_order_qty"] = pd.to_numeric(inventory_df["min_order_qty"], errors="coerce").fillna(1)

    inventory_df["days_to_stockout"] = (
        inventory_df["current_inventory"] / inventory_df["weekly_units_sold"].replace(0, 1)
    ) * 7

    inventory_df["days_to_stockout"] = inventory_df["days_to_stockout"].round(2)

    inventory_df.to_parquet(OUTPUT_PATH, index=False)

    print(f"Saved inventory parquet: {OUTPUT_PATH}")
    print(inventory_df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()