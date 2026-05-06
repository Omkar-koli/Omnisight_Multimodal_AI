from __future__ import annotations

from pathlib import Path

from omnisight.config.categories import (
    get_enabled_categories,
    raw_historical_dir,
    processed_category_dir,
    merged_dir,
    live_dir,
    snapshot_dir,
)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    categories = get_enabled_categories()

    for category in categories:
        ensure_dir(raw_historical_dir(category))
        ensure_dir(processed_category_dir(category))

    ensure_dir(merged_dir())

    for kind in ["trends", "reviews", "catalog"]:
        ensure_dir(live_dir(kind))
        ensure_dir(snapshot_dir(kind))

    print("Fresh-data layout ready.")
    for category in categories:
        print(f"[category] {category}")
        print(f"  raw       -> {raw_historical_dir(category)}")
        print(f"  processed -> {processed_category_dir(category)}")

    print(f"[merged] {merged_dir()}")
    print(f"[live trends] {live_dir('trends')}")
    print(f"[live reviews] {live_dir('reviews')}")
    print(f"[live catalog] {live_dir('catalog')}")


if __name__ == "__main__":
    main()