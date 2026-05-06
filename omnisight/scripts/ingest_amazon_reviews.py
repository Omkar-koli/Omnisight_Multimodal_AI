from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from omnisight.config.categories import (
    get_enabled_categories,
    get_category_label,
    get_category_slug,
    raw_historical_dir,
    processed_category_dir,
)


def all_files_recursive(base_dir: Path) -> list[Path]:
    if not base_dir.exists():
        return []
    return [p for p in base_dir.rglob("*") if p.is_file()]


def detect_product_file(files: list[Path]) -> Path | None:
    product_keywords = ["meta", "metadata", "product", "products"]
    supported_suffixes = [
        ".parquet",
        ".csv",
        ".jsonl",
        ".json",
        ".json.gz",
        ".jsonl.gz",
        ".csv.gz",
    ]

    for f in files:
        name = f.name.lower()
        if any(k in name for k in product_keywords) and any(name.endswith(s) for s in supported_suffixes):
            return f
    return None


def detect_review_file(files: list[Path]) -> Path | None:
    review_keywords = ["review", "reviews"]
    supported_suffixes = [
        ".parquet",
        ".csv",
        ".jsonl",
        ".json",
        ".json.gz",
        ".jsonl.gz",
        ".csv.gz",
    ]

    for f in files:
        name = f.name.lower()
        if any(k in name for k in review_keywords) and any(name.endswith(s) for s in supported_suffixes):
            return f

    # Fallback for Amazon category files like Toys_and_Games.jsonl
    for f in files:
        name = f.name.lower()
        if any(name.endswith(s) for s in supported_suffixes) and "meta" not in name and "product" not in name:
            return f

    return None


def choose_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def get_year_bounds() -> tuple[int, int]:
    start_year = int(os.getenv("REVIEW_YEAR_START", "2021"))
    end_year = int(os.getenv("REVIEW_YEAR_END", "2023"))
    return start_year, end_year


def to_datetime_series(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")

    # Try milliseconds first, then seconds
    dt_ms = pd.to_datetime(numeric, unit="ms", errors="coerce", utc=True)
    dt_s = pd.to_datetime(numeric, unit="s", errors="coerce", utc=True)

    parsed = dt_ms.where(dt_ms.notna(), dt_s)

    # Fallback to ordinary string parsing
    fallback = pd.to_datetime(series, errors="coerce", utc=True)
    parsed = parsed.where(parsed.notna(), fallback)

    return parsed


def filter_reviews_by_year_range(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    ts_col = choose_column(df, ["timestamp", "review_timestamp", "time"])
    if not ts_col:
        print("[warn] No timestamp column found in reviews; skipping year filter.")
        return df

    start_year, end_year = get_year_bounds()
    dt = to_datetime_series(df[ts_col])

    mask = dt.dt.year.between(start_year, end_year, inclusive="both")
    filtered = df.loc[mask.fillna(False)].copy()

    print(f"[filter] Reviews year range {start_year}-{end_year}: kept {len(filtered)} / {len(df)} rows")
    return filtered


def filter_products_to_reviewed_asins(products_df: pd.DataFrame, reviews_df: pd.DataFrame) -> pd.DataFrame:
    if products_df.empty:
        return products_df
    if reviews_df.empty:
        print("[filter] No reviews left after year filter; products will be empty for this category.")
        return products_df.head(0).copy()

    product_id_col = choose_column(products_df, ["parent_asin", "asin", "product_id"])
    review_product_col = choose_column(reviews_df, ["parent_asin", "asin", "product_id"])

    if not product_id_col or not review_product_col:
        print("[warn] Could not align product/review product ID columns; skipping product filter.")
        return products_df

    valid_ids = set(
        reviews_df[review_product_col]
        .astype(str)
        .str.strip()
        .replace({"": pd.NA})
        .dropna()
        .tolist()
    )

    filtered = products_df[
        products_df[product_id_col].astype(str).str.strip().isin(valid_ids)
    ].copy()

    print(f"[filter] Products linked to filtered reviews: kept {len(filtered)} / {len(products_df)} rows")
    return filtered


def read_table(path: Path, max_rows: int | None = None, is_review_file: bool = False) -> pd.DataFrame:
    name = path.name.lower()

    if name.endswith(".parquet"):
        df = pd.read_parquet(path)
        if is_review_file:
            df = filter_reviews_by_year_range(df)
        return df.head(max_rows) if max_rows else df

    if name.endswith(".csv"):
        df = pd.read_csv(path)
        if is_review_file:
            df = filter_reviews_by_year_range(df)
        return df.head(max_rows) if max_rows else df

    if name.endswith(".csv.gz"):
        df = pd.read_csv(path, compression="gzip")
        if is_review_file:
            df = filter_reviews_by_year_range(df)
        return df.head(max_rows) if max_rows else df

    if (
        name.endswith(".jsonl")
        or name.endswith(".json")
        or name.endswith(".jsonl.gz")
        or name.endswith(".json.gz")
    ):
        chunksize = int(os.getenv("JSONL_CHUNKSIZE", "20000"))
        compression = "gzip" if name.endswith(".gz") else None

        chunks: list[pd.DataFrame] = []
        total = 0

        reader = pd.read_json(
            path,
            lines=True,
            compression=compression,
            chunksize=chunksize,
        )

        for chunk in reader:
            if is_review_file:
                chunk = filter_reviews_by_year_range(chunk)

            if chunk.empty:
                continue

            if max_rows is not None:
                remaining = max_rows - total
                if remaining <= 0:
                    break
                if len(chunk) > remaining:
                    chunk = chunk.head(remaining)

            chunks.append(chunk)
            total += len(chunk)

            if max_rows is not None and total >= max_rows:
                break

        return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()

    raise ValueError(f"Unsupported file type: {path}")


def normalize_text(value) -> str:
    if value is None:
        return ""

    if isinstance(value, float) and pd.isna(value):
        return ""

    if isinstance(value, (list, tuple)):
        parts = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, float) and pd.isna(item):
                continue
            if isinstance(item, dict):
                parts.extend([str(v).strip() for v in item.values() if v is not None])
            else:
                parts.append(str(item).strip())
        return " ".join([p for p in parts if p])

    if isinstance(value, dict):
        return " ".join([str(v).strip() for v in value.values() if v is not None])

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def normalize_float(value, default: float = 0.0) -> float:
    if value is None:
        return default

    if isinstance(value, (list, tuple)):
        if not value:
            return default
        value = value[0]

    if isinstance(value, dict):
        for k in ["value", "amount", "price"]:
            if k in value:
                value = value[k]
                break

    try:
        if isinstance(value, float) and pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def extract_image_url(value) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        if not value:
            return ""
        first = value[0]
        if isinstance(first, str):
            return first.strip()
        if isinstance(first, dict):
            for key in ["large", "720w", "url", "imageUrl", "hi_res", "thumb"]:
                if key in first and first[key]:
                    return str(first[key]).strip()
        return str(first).strip()

    if isinstance(value, dict):
        for key in ["large", "720w", "url", "imageUrl", "hi_res", "thumb"]:
            if key in value and value[key]:
                return str(value[key]).strip()

    return str(value).strip()


def standardize_products(df: pd.DataFrame, category_name: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "product_id",
                "title",
                "brand",
                "price",
                "description",
                "image_url",
                "category",
                "category_slug",
                "category_label",
                "source_system",
            ]
        )

    product_id_col = choose_column(df, ["parent_asin", "asin", "product_id"])
    title_col = choose_column(df, ["title"])
    brand_col = choose_column(df, ["brand", "store"])
    price_col = choose_column(df, ["price"])
    desc_col = choose_column(df, ["description", "details", "features"])
    image_col = choose_column(df, ["image_url", "images", "image", "main_image"])

    out = pd.DataFrame()
    out["product_id"] = (
        df[product_id_col].astype(str).str.strip()
        if product_id_col
        else pd.Series([""] * len(df))
    )
    out["title"] = df[title_col].map(normalize_text) if title_col else ""
    out["brand"] = df[brand_col].map(normalize_text) if brand_col else ""
    out["price"] = df[price_col].map(normalize_float) if price_col else 0.0
    out["description"] = df[desc_col].map(normalize_text) if desc_col else ""

    if image_col:
        out["image_url"] = df[image_col].map(extract_image_url)
    else:
        out["image_url"] = ""

    out["category"] = category_name
    out["category_slug"] = get_category_slug(category_name)
    out["category_label"] = get_category_label(category_name)
    out["source_system"] = "amazon_reviews_2023"

    out = out[out["product_id"] != ""].drop_duplicates(subset=["product_id"]).reset_index(drop=True)
    return out


def standardize_reviews(df: pd.DataFrame, category_name: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "review_id",
                "product_id",
                "rating",
                "review_title",
                "review_text",
                "helpful_vote",
                "review_timestamp",
                "category",
                "category_slug",
                "category_label",
                "source_system",
            ]
        )

    review_id_col = choose_column(df, ["review_id"])
    product_id_col = choose_column(df, ["parent_asin", "asin", "product_id"])
    rating_col = choose_column(df, ["rating", "stars"])
    title_col = choose_column(df, ["title", "review_title"])
    text_col = choose_column(df, ["text", "review_text"])
    helpful_col = choose_column(df, ["helpful_vote", "helpful_votes"])
    ts_col = choose_column(df, ["timestamp", "review_timestamp"])

    out = pd.DataFrame()

    if review_id_col:
        out["review_id"] = df[review_id_col].astype(str).str.strip()
    else:
        out["review_id"] = [f"{get_category_slug(category_name)}_{i}" for i in range(len(df))]

    out["product_id"] = (
        df[product_id_col].astype(str).str.strip()
        if product_id_col
        else pd.Series([""] * len(df))
    )
    out["rating"] = df[rating_col].map(normalize_float) if rating_col else 0.0
    out["review_title"] = df[title_col].map(normalize_text) if title_col else ""
    out["review_text"] = df[text_col].map(normalize_text) if text_col else ""
    out["helpful_vote"] = df[helpful_col].map(normalize_float) if helpful_col else 0.0
    out["review_timestamp"] = df[ts_col].astype(str) if ts_col else ""
    out["category"] = category_name
    out["category_slug"] = get_category_slug(category_name)
    out["category_label"] = get_category_label(category_name)
    out["source_system"] = "amazon_reviews_2023"

    out = out[out["product_id"] != ""].drop_duplicates(subset=["review_id"]).reset_index(drop=True)
    return out


def build_inventory_placeholder(products_df: pd.DataFrame) -> pd.DataFrame:
    if products_df.empty:
        return pd.DataFrame(
            columns=[
                "product_id",
                "category_slug",
                "current_inventory",
                "weekly_units_sold",
                "lead_time_days",
                "supplier",
                "min_order_qty",
                "source_system",
            ]
        )

    out = pd.DataFrame()
    out["product_id"] = products_df["product_id"]
    out["category_slug"] = products_df["category_slug"]
    out["current_inventory"] = 100
    out["weekly_units_sold"] = 20
    out["lead_time_days"] = 7
    out["supplier"] = "default_supplier"
    out["min_order_qty"] = 10
    out["source_system"] = "placeholder_inventory"
    return out


def build_trends_placeholder(products_df: pd.DataFrame) -> pd.DataFrame:
    if products_df.empty:
        return pd.DataFrame(
            columns=[
                "product_id",
                "category_slug",
                "trend_keyword",
                "trend_index",
                "trend_change_pct",
                "captured_at",
                "source_system",
            ]
        )

    sample = products_df[["product_id", "category_slug", "title"]].copy()
    sample["trend_keyword"] = sample["title"].fillna("").astype(str).str.slice(0, 60)
    sample["trend_index"] = 0.0
    sample["trend_change_pct"] = 0.0
    sample["captured_at"] = ""
    sample["source_system"] = "placeholder_trends"
    return sample.drop(columns=["title"])


def process_category(category_name: str) -> None:
    raw_dir = raw_historical_dir(category_name)
    out_dir = processed_category_dir(category_name)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = all_files_recursive(raw_dir)
    print(f"[scan] {category_name}: found {len(files)} files under {raw_dir}")

    product_file = detect_product_file(files)
    review_file = detect_review_file(files)

    max_product_rows = int(os.getenv("MAX_PRODUCT_ROWS_PER_CATEGORY", "50000"))
    max_review_rows = int(os.getenv("MAX_REVIEW_ROWS_PER_CATEGORY", "200000"))

    if product_file is None:
        print(f"[warn] {category_name}: no product/meta file found in {raw_dir}")
        products_raw = pd.DataFrame()
    else:
        print(f"[read] {category_name} products <- {product_file} (max_rows={max_product_rows})")
        products_raw = read_table(product_file, max_rows=max_product_rows, is_review_file=False)

    if review_file is None:
        print(f"[warn] {category_name}: no review file found in {raw_dir}")
        reviews_raw = pd.DataFrame()
    else:
        print(f"[read] {category_name} reviews <- {review_file} (max_rows={max_review_rows})")
        reviews_raw = read_table(review_file, max_rows=max_review_rows, is_review_file=True)

    products_raw = filter_products_to_reviewed_asins(products_raw, reviews_raw)

    products_df = standardize_products(products_raw, category_name)
    reviews_df = standardize_reviews(reviews_raw, category_name)
    inventory_df = build_inventory_placeholder(products_df)
    trends_df = build_trends_placeholder(products_df)

    products_df.to_parquet(out_dir / "products.parquet", index=False)
    reviews_df.to_parquet(out_dir / "reviews.parquet", index=False)
    inventory_df.to_parquet(out_dir / "inventory.parquet", index=False)
    trends_df.to_parquet(out_dir / "trends.parquet", index=False)

    print(
        f"[saved] {category_name}: "
        f"products={len(products_df)}, "
        f"reviews={len(reviews_df)}, "
        f"inventory={len(inventory_df)}, "
        f"trends={len(trends_df)}"
    )


def main() -> None:
    categories = get_enabled_categories()
    print("Ingesting categories:", categories)

    for category in categories:
        process_category(category)

    print("Done.")


if __name__ == "__main__":
    main()