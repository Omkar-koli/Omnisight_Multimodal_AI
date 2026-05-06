from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import pandas as pd

from omnisight.config.categories import merged_dir, live_dir
from omnisight.live.google_trends_client import (
    serpapi_configured,
    fetch_interest_over_time,
    fetch_related_queries,
    fetch_trending_now,
    normalize_interest_over_time,
    normalize_related_queries,
    normalize_trending_now,
)


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
    df["title"] = df["title"].fillna("").astype(str).str.strip()
    df["product_id"] = df["product_id"].astype(str).str.strip()
    df["category_slug"] = df["category_slug"].astype(str).str.strip()
    return df

def clean_trend_keyword(title: str, max_words: int = 5) -> str:
    words = []
    for token in str(title).replace("|", " ").replace(",", " ").split():
        token = "".join(ch for ch in token if ch.isalnum() or ch in {"-", "&"})
        token = token.strip()
        if len(token) >= 2:
            words.append(token)
    return " ".join(words[:max_words]).strip()

def build_keywords(df: pd.DataFrame, per_category: int = 12) -> pd.DataFrame:
    work = df[df["title"] != ""].copy()
    work = work.drop_duplicates(subset=["category_slug", "title"]).copy()

    work = (
        work.groupby("category_slug", group_keys=False)
        .head(per_category)
        .reset_index(drop=True)
    )

    work["trend_keyword"] = work["title"].map(clean_trend_keyword)
    work = work[work["trend_keyword"] != ""].copy()

    return work[["product_id", "category_slug", "trend_keyword"]]


def retry_call(fn, *args, max_retries: int = 3, sleep_seconds: float = 1.5, **kwargs):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            print(f"[retry {attempt}/{max_retries}] {fn.__name__} failed -> {e}")
            if attempt < max_retries:
                time.sleep(sleep_seconds)
    raise last_error


def main() -> None:
    out_dir = live_dir("trends")
    out_dir.mkdir(parents=True, exist_ok=True)

    trends_out = out_dir / "live_trends_latest.parquet"
    related_out = out_dir / "live_related_queries_latest.parquet"
    trending_now_out = out_dir / "live_trending_now_latest.parquet"
    health_out = out_dir / "live_trends_health.parquet"

    if not serpapi_configured():
        raise ValueError("SERPAPI_API_KEY is missing in .env")

    per_category = env_int("LIVE_TRENDS_QUERIES_PER_CATEGORY", 12)
    max_trend_rows = env_int("MAX_LIVE_TRENDS", 5000)
    max_related_rows = env_int("MAX_LIVE_RELATED_QUERIES", 5000)
    max_trending_now_rows = env_int("MAX_LIVE_TRENDING_NOW", 500)
    max_retries = env_int("LIVE_TRENDS_MAX_RETRIES", 3)

    run_started_at = datetime.now(timezone.utc).isoformat()

    products = load_current_products()
    keywords = build_keywords(products, per_category=per_category)

    trend_rows = []
    related_rows = []

    ts_success = 0
    ts_fail = 0
    related_success = 0
    related_fail = 0
    trending_now_success = 0
    trending_now_fail = 0

    for _, row in keywords.iterrows():
        product_id = str(row["product_id"])
        category_slug = str(row["category_slug"])
        keyword = str(row["trend_keyword"])

        try:
            timeseries_payload = retry_call(
                fetch_interest_over_time,
                keyword=keyword,
                max_retries=max_retries,
            )
            normalized = normalize_interest_over_time(
                keyword=keyword,
                payload=timeseries_payload,
                category_slug=category_slug,
                product_id=product_id,
            )
            for item in normalized:
                item["captured_at"] = item.get("captured_at") or run_started_at
            trend_rows.extend(normalized)
            ts_success += 1
            print(f"[ok] timeseries: {keyword}")
        except Exception as e:
            ts_fail += 1
            print(f"[fail] timeseries: {keyword} -> {e}")

        try:
            related_payload = retry_call(
                fetch_related_queries,
                keyword=keyword,
                max_retries=max_retries,
            )
            normalized = normalize_related_queries(
                keyword=keyword,
                payload=related_payload,
                category_slug=category_slug,
            )
            for item in normalized:
                item["captured_at"] = run_started_at
                item["product_id"] = product_id
            related_rows.extend(normalized)
            related_success += 1
            print(f"[ok] related: {keyword}")
        except Exception as e:
            related_fail += 1
            print(f"[fail] related: {keyword} -> {e}")

    trending_now_rows = []
    try:
        trending_now_payload = retry_call(
            fetch_trending_now,
            max_retries=max_retries,
        )
        trending_now_rows = normalize_trending_now(trending_now_payload)
        for item in trending_now_rows:
            item["captured_at"] = run_started_at
        trending_now_success = 1
        print("[ok] trending now")
    except Exception as e:
        trending_now_fail = 1
        print(f"[fail] trending now -> {e}")

    trends_df = pd.DataFrame(trend_rows)
    related_df = pd.DataFrame(related_rows)
    trending_now_df = pd.DataFrame(trending_now_rows)

    if trends_df.empty:
        trends_df = pd.DataFrame(
            columns=[
                "product_id",
                "category_slug",
                "trend_keyword",
                "captured_at",
                "trend_index",
                "trend_change_pct",
                "source_system",
            ]
        )
    else:
        dedupe_cols = [c for c in ["product_id", "trend_keyword", "captured_at"] if c in trends_df.columns]
        if dedupe_cols:
            trends_df = trends_df.drop_duplicates(subset=dedupe_cols).reset_index(drop=True)
        if max_trend_rows > 0 and len(trends_df) > max_trend_rows:
            trends_df = trends_df.head(max_trend_rows).copy()

    if related_df.empty:
        related_df = pd.DataFrame(
            columns=[
                "product_id",
                "category_slug",
                "seed_keyword",
                "related_query",
                "value_label",
                "extracted_value",
                "captured_at",
                "source_system",
            ]
        )
    else:
        dedupe_cols = [c for c in ["product_id", "seed_keyword", "related_query"] if c in related_df.columns]
        if dedupe_cols:
            related_df = related_df.drop_duplicates(subset=dedupe_cols).reset_index(drop=True)
        if max_related_rows > 0 and len(related_df) > max_related_rows:
            related_df = related_df.head(max_related_rows).copy()

    if trending_now_df.empty:
        trending_now_df = pd.DataFrame(
            columns=[
                "title",
                "link",
                "captured_at",
                "source_system",
            ]
        )
    else:
        dedupe_cols = [c for c in ["title", "link"] if c in trending_now_df.columns]
        if dedupe_cols:
            trending_now_df = trending_now_df.drop_duplicates(subset=dedupe_cols).reset_index(drop=True)
        if max_trending_now_rows > 0 and len(trending_now_df) > max_trending_now_rows:
            trending_now_df = trending_now_df.head(max_trending_now_rows).copy()

    trends_df.to_parquet(trends_out, index=False)
    related_df.to_parquet(related_out, index=False)
    trending_now_df.to_parquet(trending_now_out, index=False)

    health_df = pd.DataFrame(
        [
            {
                "source_name": "live_trends",
                "captured_at": run_started_at,
                "keyword_count": len(keywords),
                "timeseries_success_count": ts_success,
                "timeseries_failure_count": ts_fail,
                "related_success_count": related_success,
                "related_failure_count": related_fail,
                "trending_now_success_count": trending_now_success,
                "trending_now_failure_count": trending_now_fail,
                "trend_row_count": len(trends_df),
                "related_row_count": len(related_df),
                "trending_now_row_count": len(trending_now_df),
                "status": "success" if len(trends_df) > 0 else "empty",
            }
        ]
    )
    health_df.to_parquet(health_out, index=False)

    print(f"[saved] {trends_out} rows={len(trends_df)}")
    print(f"[saved] {related_out} rows={len(related_df)}")
    print(f"[saved] {trending_now_out} rows={len(trending_now_df)}")
    print(f"[saved] {health_out}")
    print(
        f"[summary] keywords={len(keywords)} "
        f"timeseries_ok={ts_success} timeseries_fail={ts_fail} "
        f"related_ok={related_success} related_fail={related_fail} "
        f"trending_now_ok={trending_now_success} trending_now_fail={trending_now_fail}"
    )


if __name__ == "__main__":
    main()