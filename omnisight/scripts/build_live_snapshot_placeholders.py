from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from omnisight.config.categories import live_dir


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_if_missing(path: Path, columns: list[str]) -> None:
    if path.exists():
        print(f"[exists] {path}")
        return

    df = pd.DataFrame(columns=columns)
    df.to_parquet(path, index=False)
    print(f"[created] {path}")


def main() -> None:
    trends_path = live_dir("trends") / "live_trends_latest.parquet"
    reviews_path = live_dir("reviews") / "live_reviews_latest.parquet"
    catalog_path = live_dir("catalog") / "live_catalog_latest.parquet"

    write_if_missing(
        trends_path,
        [
            "product_id",
            "category_slug",
            "trend_keyword",
            "trend_index",
            "trend_change_pct",
            "captured_at",
            "source_system",
        ],
    )

    write_if_missing(
        reviews_path,
        [
            "review_id",
            "product_id",
            "category_slug",
            "rating",
            "review_text",
            "review_timestamp",
            "source_system",
        ],
    )

    write_if_missing(
        catalog_path,
        [
            "product_id",
            "category_slug",
            "title",
            "brand",
            "price",
            "current_inventory",
            "weekly_units_sold",
            "lead_time_days",
            "captured_at",
            "source_system",
        ],
    )


if __name__ == "__main__":
    main()