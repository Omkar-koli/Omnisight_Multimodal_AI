from __future__ import annotations

from pathlib import Path

from omnisight.config.categories import (
    get_enabled_categories,
    get_category_processed_dir,
    get_merged_processed_dir,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    categories = get_enabled_categories()

    raw_base = PROJECT_ROOT / "data" / "raw"
    processed_base = PROJECT_ROOT / "data" / "processed"

    ensure_dir(raw_base)
    ensure_dir(processed_base)

    for category in categories:
        cat_dir = get_category_processed_dir(category)
        ensure_dir(cat_dir)

    ensure_dir(get_merged_processed_dir())

    print("Created multi-category folder structure.")
    for category in categories:
        print(f"- {category}: {get_category_processed_dir(category)}")
    print(f"- merged: {get_merged_processed_dir()}")


if __name__ == "__main__":
    main()