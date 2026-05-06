from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
IMAGE_DIR = PROJECT_ROOT / "data" / "raw" / "product_images"

IMAGE_DIR.mkdir(parents=True, exist_ok=True)

PRODUCTS_PATH = PROCESSED_DIR / "products.parquet"


def main() -> None:
    if not PRODUCTS_PATH.exists():
        raise FileNotFoundError("Run 01_ingest_amazon_reviews.py first.")

    products_df = pd.read_parquet(PRODUCTS_PATH)

    downloaded = 0
    for _, row in products_df.iterrows():
        product_id = str(row["product_id"])
        image_url = str(row.get("image_url", "")).strip()

        if not image_url:
            continue

        out_path = IMAGE_DIR / f"{product_id}.jpg"
        if out_path.exists():
            continue

        try:
            response = requests.get(image_url, timeout=20)
            response.raise_for_status()
            out_path.write_bytes(response.content)
            downloaded += 1
        except Exception as e:
            print(f"Skipped {product_id}: {e}")

    print(f"Downloaded {downloaded} images.")


if __name__ == "__main__":
    main()