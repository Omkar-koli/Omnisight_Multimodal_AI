from __future__ import annotations

from pathlib import Path

import pandas as pd

from omnisight.config.categories import (
    get_enabled_categories,
    processed_category_dir,
    merged_dir,
    get_category_slug,
    live_dir,
)


def load_parquet(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        print(f"[missing] {label}: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)
    print(f"[loaded] {label}: {path} rows={len(df)}")
    return df


def normalize_product_id(df: pd.DataFrame) -> pd.DataFrame:
    if "product_id" in df.columns:
        df = df.copy()
        df["product_id"] = df["product_id"].astype(str).str.strip()
    return df


def load_historical_reviews() -> pd.DataFrame:
    frames = []

    for category in get_enabled_categories():
        path = processed_category_dir(category) / "reviews.parquet"
        df = load_parquet(path, f"{category} reviews")
        if df.empty:
            continue

        df = normalize_product_id(df)
        if "category_slug" not in df.columns:
            df["category_slug"] = get_category_slug(category)
        frames.append(df)

    if not frames:
        print("[warn] no historical reviews loaded")
        return pd.DataFrame()

    merged = pd.concat(frames, ignore_index=True)
    print(f"[merged] historical reviews rows={len(merged)}")
    return merged


def load_historical_products() -> pd.DataFrame:
    frames = []

    for category in get_enabled_categories():
        path = processed_category_dir(category) / "products.parquet"
        df = load_parquet(path, f"{category} products")
        if df.empty:
            continue

        df = normalize_product_id(df)
        if "category_slug" not in df.columns:
            df["category_slug"] = get_category_slug(category)
        frames.append(df)

    if not frames:
        print("[warn] no historical products loaded")
        return pd.DataFrame()

    merged = pd.concat(frames, ignore_index=True)
    if {"product_id", "category_slug"}.issubset(merged.columns):
        merged = merged.drop_duplicates(subset=["product_id", "category_slug"]).reset_index(drop=True)

    print(f"[merged] historical products rows={len(merged)}")
    return merged


def load_historical_trends() -> pd.DataFrame:
    frames = []

    for category in get_enabled_categories():
        path = processed_category_dir(category) / "trends.parquet"
        df = load_parquet(path, f"{category} trends")
        if df.empty:
            continue

        df = normalize_product_id(df)
        if "category_slug" not in df.columns:
            df["category_slug"] = get_category_slug(category)
        frames.append(df)

    if not frames:
        print("[warn] no historical trends loaded")
        return pd.DataFrame()

    merged = pd.concat(frames, ignore_index=True)
    print(f"[merged] historical trends rows={len(merged)}")
    return merged


def merge_reviews() -> pd.DataFrame:
    historical = load_historical_reviews()
    live = load_parquet(live_dir("reviews") / "live_reviews_latest.parquet", "live reviews")

    if historical.empty and live.empty:
        print("[warn] reviews merge got no data")
        return pd.DataFrame()

    if not live.empty:
        live = normalize_product_id(live)

    merged = pd.concat([historical, live], ignore_index=True)
    if "review_id" in merged.columns:
        merged = merged.drop_duplicates(subset=["review_id"], keep="last")

    merged = merged.reset_index(drop=True)
    print(f"[final] reviews_current rows={len(merged)}")
    return merged


def merge_products() -> pd.DataFrame:
    historical = load_historical_products()
    live = load_parquet(live_dir("catalog") / "live_catalog_latest.parquet", "live catalog")

    if historical.empty and live.empty:
        print("[warn] products merge got no data")
        return pd.DataFrame()

    if not live.empty:
        live = normalize_product_id(live)

    merged = pd.concat([historical, live], ignore_index=True)
    if {"product_id", "category_slug"}.issubset(merged.columns):
        merged = merged.drop_duplicates(subset=["product_id", "category_slug"], keep="last")

    merged = merged.reset_index(drop=True)
    print(f"[final] products_current rows={len(merged)}")
    return merged


def merge_trends() -> pd.DataFrame:
    historical = load_historical_trends()
    live = load_parquet(live_dir("trends") / "live_trends_latest.parquet", "live trends")

    if historical.empty and live.empty:
        print("[warn] trends merge got no data")
        return pd.DataFrame()

    if not live.empty:
        live = normalize_product_id(live)

    merged = pd.concat([historical, live], ignore_index=True)
    dedupe_cols = [c for c in ["product_id", "trend_keyword", "captured_at"] if c in merged.columns]
    if dedupe_cols:
        merged = merged.drop_duplicates(subset=dedupe_cols, keep="last")

    merged = merged.reset_index(drop=True)
    print(f"[final] trends_current rows={len(merged)}")
    return merged


def main() -> None:
    out_dir = merged_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[outdir] {out_dir}")

    products = merge_products()
    reviews = merge_reviews()
    trends = merge_trends()

    if not products.empty:
        path = out_dir / "products_current.parquet"
        products.to_parquet(path, index=False)
        print(f"[saved] {path} rows={len(products)}")
    else:
        print("[skip] products_current.parquet not written")

    if not reviews.empty:
        path = out_dir / "reviews_current.parquet"
        reviews.to_parquet(path, index=False)
        print(f"[saved] {path} rows={len(reviews)}")
    else:
        print("[skip] reviews_current.parquet not written")

    if not trends.empty:
        path = out_dir / "trends_current.parquet"
        trends.to_parquet(path, index=False)
        print(f"[saved] {path} rows={len(trends)}")
    else:
        print("[skip] trends_current.parquet not written")


if __name__ == "__main__":
    main()