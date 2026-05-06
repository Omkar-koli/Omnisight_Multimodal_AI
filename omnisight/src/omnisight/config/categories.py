from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

CATEGORY_METADATA: Dict[str, dict] = {
    "Toys_and_Games": {
        "slug": "toys_and_games",
        "label": "Toys & Games",
    },
    "Home_and_Kitchen": {
        "slug": "home_and_kitchen",
        "label": "Home & Kitchen",
    },
    "Beauty_and_Personal_Care": {
        "slug": "beauty_and_personal_care",
        "label": "Beauty & Personal Care",
    },
}


def get_enabled_categories() -> List[str]:
    raw = os.getenv(
        "ENABLED_CATEGORIES",
        "Toys_and_Games,Home_and_Kitchen,Beauty_and_Personal_Care",
    )
    categories = [x.strip() for x in raw.split(",") if x.strip()]

    unknown = [c for c in categories if c not in CATEGORY_METADATA]
    if unknown:
        raise ValueError(f"Unknown categories in ENABLED_CATEGORIES: {unknown}")

    return categories


def get_category_slug(category_name: str) -> str:
    return CATEGORY_METADATA[category_name]["slug"]


def get_category_label(category_name: str) -> str:
    return CATEGORY_METADATA[category_name]["label"]


def project_root() -> Path:
    return PROJECT_ROOT


def raw_historical_dir(category_name: str) -> Path:
    return PROJECT_ROOT / "data" / "raw" / "historical" / get_category_slug(category_name)


def processed_category_dir(category_name: str) -> Path:
    return PROJECT_ROOT / "data" / "processed" / "categories" / get_category_slug(category_name)


def merged_dir() -> Path:
    return PROJECT_ROOT / "data" / "processed" / "merged"


def live_dir(kind: str) -> Path:
    return PROJECT_ROOT / "data" / "raw" / "live" / kind


def snapshot_dir(kind: str) -> Path:
    return PROJECT_ROOT / "data" / "raw" / "snapshots" / kind