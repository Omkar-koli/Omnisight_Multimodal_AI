from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from omnisight.live.ebay_client import search_ebay_items, normalize_ebay_results
from omnisight.config.categories import merged_dir, live_dir


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except Exception:
        return default


def load_current_products() -> pd.DataFrame:
    path = merged_dir() / "products_current.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Missing merged products file: {path}")

    df = pd.read_parquet(path).copy()

    if "product_id" in df.columns:
        df["product_id"] = df["product_id"].astype(str).str.strip()

    if "title" in df.columns:
        df["title"] = df["title"].fillna("").astype(str).str.strip()

    if "category_slug" not in df.columns:
        raise ValueError("products_current.parquet is missing category_slug")

    return df


def clean_query(title: str, max_words: int = 6) -> str:
    words = []
    for token in str(title).replace("|", " ").replace(",", " ").split():
        token = "".join(ch for ch in token if ch.isalnum() or ch in {"-", "&"})
        token = token.strip()
        if len(token) >= 2:
            words.append(token)
    return " ".join(words[:max_words]).strip()


def build_queries(df: pd.DataFrame, per_category: int = 15) -> pd.DataFrame:
    work = df.copy()
    work["title"] = work["title"].fillna("").astype(str).str.strip()
    work = work[work["title"] != ""].copy()

    work = work.drop_duplicates(subset=["category_slug", "title"]).copy()

    work = (
        work.groupby("category_slug", group_keys=False)
        .head(per_category)
        .reset_index(drop=True)
    )

    work["query"] = work["title"].map(clean_query)
    work = work[work["query"] != ""].copy()

    return work[["product_id", "category_slug", "title", "query"]]


def search_with_retry(query: str, limit: int, max_retries: int = 3, sleep_seconds: float = 1.5):
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            return search_ebay_items(query=query, limit=limit)
        except Exception as e:
            last_error = e
            print(f"[retry {attempt}/{max_retries}] eBay query failed: {query} -> {e}")
            if attempt < max_retries:
                time.sleep(sleep_seconds)

    raise last_error


def main() -> None:
    per_category = env_int("LIVE_CATALOG_QUERIES_PER_CATEGORY", 10)
    items_per_query = env_int("LIVE_CATALOG_ITEMS_PER_QUERY", 5)
    max_total_rows = env_int("MAX_LIVE_CATALOG", 5000)
    max_retries = env_int("LIVE_CATALOG_MAX_RETRIES", 3)

    products = load_current_products()
    queries = build_queries(products, per_category=per_category)

    rows = []
    success_count = 0
    failure_count = 0
    run_started_at = datetime.now(timezone.utc).isoformat()

    for _, row in queries.iterrows():
        query = str(row["query"]).strip()
        category_slug = str(row["category_slug"])
        product_id = str(row["product_id"])

        try:
            payload = search_with_retry(
                query=query,
                limit=items_per_query,
                max_retries=max_retries,
            )

            normalized = normalize_ebay_results(
                query=query,
                payload=payload,
                category_slug=category_slug,
            )

            for item in normalized:
                item["product_id"] = product_id
                item["captured_at"] = run_started_at

            rows.extend(normalized)
            success_count += 1
            print(f"[ok] eBay query: {query}")

        except Exception as e:
            failure_count += 1
            print(f"[fail] eBay query: {query} -> {e}")

    out_dir = live_dir("catalog")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "live_catalog_latest.parquet"
    health_path = out_dir / "live_catalog_health.parquet"

    df = pd.DataFrame(rows)

    if df.empty:
        df = pd.DataFrame(
            columns=[
                "product_id",
                "category_slug",
                "source_system",
                "external_item_id",
                "query",
                "title",
                "price",
                "item_web_url",
                "image_url",
                "condition",
                "buying_options",
                "captured_at",
            ]
        )
    else:
        # Deduplicate the same eBay listing showing up for multiple similar queries
        dedupe_cols = [c for c in ["product_id", "external_item_id"] if c in df.columns]
        if dedupe_cols:
            df = df.drop_duplicates(subset=dedupe_cols).reset_index(drop=True)

        if max_total_rows > 0 and len(df) > max_total_rows:
            df = df.head(max_total_rows).copy()

    df.to_parquet(out_path, index=False)

    health_df = pd.DataFrame(
        [
            {
                "source_name": "live_catalog",
                "captured_at": run_started_at,
                "query_count": len(queries),
                "success_count": success_count,
                "failure_count": failure_count,
                "row_count": len(df),
                "status": "success" if len(df) > 0 else "empty",
            }
        ]
    )
    health_df.to_parquet(health_path, index=False)

    print(f"[saved] {out_path} rows={len(df)}")
    print(f"[saved] {health_path}")
    print(f"[summary] queries={len(queries)} success={success_count} fail={failure_count}")
    

if __name__ == "__main__":
    main()