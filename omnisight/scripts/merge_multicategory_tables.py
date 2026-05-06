from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

from omnisight.config.categories import (
    get_enabled_categories,
    get_category_label,
    get_category_processed_dir,
    get_category_slug,
    get_merged_processed_dir,
)

TABLES = ["products", "reviews", "trends", "inventory"]


def load_table_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def add_category_columns(df: pd.DataFrame, category_name: str) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df["category_source"] = category_name
    df["category_slug"] = get_category_slug(category_name)
    df["category_label"] = get_category_label(category_name)

    if "product_id" in df.columns:
        df["product_id"] = df["product_id"].astype(str).str.strip()

    return df


def dedupe_table(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df.empty:
        return df

    if table_name == "products":
        subset = [c for c in ["product_id", "category_slug"] if c in df.columns]
        if subset:
            return df.drop_duplicates(subset=subset).reset_index(drop=True)

    if table_name == "reviews":
        subset = [c for c in ["review_id"] if c in df.columns]
        if subset:
            return df.drop_duplicates(subset=subset).reset_index(drop=True)

    if table_name == "trends":
        subset = [c for c in ["trend_keyword", "week", "category_slug"] if c in df.columns]
        if subset:
            return df.drop_duplicates(subset=subset).reset_index(drop=True)

    if table_name == "inventory":
        subset = [c for c in ["product_id", "category_slug"] if c in df.columns]
        if subset:
            return df.drop_duplicates(subset=subset).reset_index(drop=True)

    return df.reset_index(drop=True)


def merge_one_table(table_name: str, categories: List[str]) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []

    for category in categories:
        table_path = get_category_processed_dir(category) / f"{table_name}.parquet"
        df = load_table_if_exists(table_path)

        if df.empty:
            print(f"[skip] {table_name}: no file for {category} -> {table_path}")
            continue

        df = add_category_columns(df, category)
        frames.append(df)
        print(f"[ok] {table_name}: loaded {len(df)} rows for {category}")

    if not frames:
        return pd.DataFrame()

    merged = pd.concat(frames, ignore_index=True)
    merged = dedupe_table(merged, table_name)
    return merged


def main() -> None:
    categories = get_enabled_categories()
    merged_dir = get_merged_processed_dir()
    merged_dir.mkdir(parents=True, exist_ok=True)

    for table_name in TABLES:
        merged = merge_one_table(table_name, categories)
        out_path = merged_dir / f"{table_name}.parquet"

        if merged.empty:
            print(f"[warn] merged {table_name} is empty; not writing file.")
            continue

        merged.to_parquet(out_path, index=False)
        print(f"[saved] {table_name}: {len(merged)} rows -> {out_path}")


if __name__ == "__main__":
    main()