from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from qdrant_client.models import PointStruct

from omnisight.embeddings.multimodal_embedder import MultimodalEmbedder
from omnisight.embeddings.text_embedder import TextEmbedder
from omnisight.retrieval.qdrant_store import QdrantStore
from omnisight.settings import settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MERGED_DIR = PROJECT_ROOT / "data" / "processed" / "merged"
IMAGE_DIR = PROJECT_ROOT / "data" / "raw" / "product_images"


def safe_str(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except Exception:
        return default


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def build_feature_map(feature_base_path: Path) -> dict[str, dict]:
    if not feature_base_path.exists():
        return {}

    feature_base_df = pd.read_parquet(feature_base_path)
    if feature_base_df.empty or "product_id" not in feature_base_df.columns:
        return {}

    feature_base_df["product_id"] = feature_base_df["product_id"].astype("string")
    return feature_base_df.set_index("product_id").to_dict(orient="index")


def maybe_apply_debug_limits(
    products_df: pd.DataFrame,
    reviews_df: pd.DataFrame,
    trends_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    product_limit = env_int("QDRANT_DEBUG_LIMIT_PRODUCTS", 0)
    review_limit = env_int("QDRANT_DEBUG_LIMIT_REVIEWS", 0)
    trend_limit = env_int("QDRANT_DEBUG_LIMIT_TRENDS", 0)

    print("Original sizes:", len(products_df), len(reviews_df), len(trends_df))

    if product_limit > 0:
        products_df = products_df.head(product_limit).copy()
    if review_limit > 0:
        reviews_df = reviews_df.head(review_limit).copy()
    if trend_limit > 0:
        trends_df = trends_df.head(trend_limit).copy()

    print("Working sizes :", len(products_df), len(reviews_df), len(trends_df))
    return products_df, reviews_df, trends_df


def reduce_reviews(reviews_df: pd.DataFrame) -> pd.DataFrame:
    if reviews_df.empty:
        return reviews_df

    reviews_per_product = env_int("QDRANT_REVIEWS_PER_PRODUCT", 5)
    max_reviews_total = env_int("QDRANT_MAX_REVIEWS_TOTAL", 20000)

    reviews_df = reviews_df.copy()
    reviews_df["product_id"] = reviews_df["product_id"].astype("string")

    ts_col = "review_timestamp" if "review_timestamp" in reviews_df.columns else None
    if ts_col:
        reviews_df["_review_ts"] = pd.to_datetime(reviews_df[ts_col], errors="coerce", utc=True)
        reviews_df = (
            reviews_df
            .sort_values(["product_id", "_review_ts"], ascending=[True, False])
            .groupby("product_id", group_keys=False)
            .head(reviews_per_product)
            .copy()
        )
        reviews_df = reviews_df.drop(columns=["_review_ts"], errors="ignore")
    else:
        reviews_df = (
            reviews_df
            .groupby("product_id", group_keys=False)
            .head(reviews_per_product)
            .copy()
        )

    if max_reviews_total > 0 and len(reviews_df) > max_reviews_total:
        reviews_df = reviews_df.head(max_reviews_total).copy()

    print(f"Reduced reviews to {len(reviews_df)} rows")
    return reviews_df


def reduce_trends(trends_df: pd.DataFrame) -> pd.DataFrame:
    if trends_df.empty:
        return trends_df

    trends_per_product = env_int("QDRANT_TRENDS_PER_PRODUCT", 3)
    max_trends_total = env_int("QDRANT_MAX_TRENDS_TOTAL", 10000)

    trends_df = trends_df.copy()
    trends_df["product_id"] = trends_df["product_id"].astype("string")

    sort_col = None
    if "captured_at" in trends_df.columns:
        trends_df["_trend_ts"] = pd.to_datetime(trends_df["captured_at"], errors="coerce", utc=True)
        sort_col = "_trend_ts"
    elif "week" in trends_df.columns:
        trends_df["_trend_ts"] = pd.to_datetime(trends_df["week"], errors="coerce", utc=True)
        sort_col = "_trend_ts"

    if sort_col:
        trends_df = (
            trends_df
            .sort_values(["product_id", sort_col], ascending=[True, False])
            .groupby("product_id", group_keys=False)
            .head(trends_per_product)
            .copy()
        )
        trends_df = trends_df.drop(columns=["_trend_ts"], errors="ignore")
    else:
        trends_df = (
            trends_df
            .groupby("product_id", group_keys=False)
            .head(trends_per_product)
            .copy()
        )

    if max_trends_total > 0 and len(trends_df) > max_trends_total:
        trends_df = trends_df.head(max_trends_total).copy()

    print(f"Reduced trends to {len(trends_df)} rows")
    return trends_df


def build_product_text(row: pd.Series, feature_map: dict[str, dict]) -> str:
    product_id = str(row["product_id"])
    feat = feature_map.get(product_id, {})

    parts = [
        "Doc Type: Product",
        f"Category Slug: {safe_str(row.get('category_slug', ''))}",
        f"Category Label: {safe_str(row.get('category_label', row.get('category', '')))}",
        f"Title: {safe_str(row.get('title', ''))}",
        f"Brand: {safe_str(row.get('brand', ''))}",
        f"Category: {safe_str(row.get('category', ''))}",
        f"Price: {safe_str(row.get('price', ''))}",
        f"Description: {safe_str(row.get('description', ''))}",
        f"Review count: {feat.get('review_count', 0)}",
        f"Average rating: {feat.get('avg_rating', 0)}",
        f"Latest trend index: {feat.get('latest_trend_index', 0)}",
        f"Average trend change pct: {feat.get('avg_trend_change_pct', 0)}",
    ]
    return "\n".join(parts)


def build_review_text(row: pd.Series) -> str:
    parts = [
        "Doc Type: Review",
        f"Category Slug: {safe_str(row.get('category_slug', ''))}",
        f"Category Label: {safe_str(row.get('category_label', row.get('category', '')))}",
        f"Review title: {safe_str(row.get('review_title', ''))}",
        f"Review text: {safe_str(row.get('review_text', ''))}",
        f"Rating: {safe_str(row.get('rating', ''))}",
        f"Helpfulness: {safe_str(row.get('helpful_vote', row.get('helpfulness', '')))}",
    ]
    return "\n".join(parts)


def build_trend_text(row: pd.Series) -> str:
    parts = [
        "Doc Type: Trend",
        f"Category Slug: {safe_str(row.get('category_slug', ''))}",
        f"Category Label: {safe_str(row.get('category_label', row.get('category', '')))}",
        f"Trend keyword: {safe_str(row.get('trend_keyword', ''))}",
        f"Product ID: {safe_str(row.get('product_id', ''))}",
        f"Captured At: {safe_str(row.get('captured_at', row.get('week', '')))}",
        f"Trend index: {safe_str(row.get('trend_index', ''))}",
        f"Trend change percent: {safe_str(row.get('trend_change_pct', ''))}",
    ]
    return "\n".join(parts)


def upsert_in_batches(
    store: QdrantStore,
    collection_name: str,
    points: list[PointStruct],
    batch_size: int,
) -> None:
    total = len(points)
    if total == 0:
        print(f"No points to upsert for {collection_name}.")
        return

    for start in range(0, total, batch_size):
        batch = points[start:start + batch_size]
        store.upsert_points(collection_name, batch)
        print(
            f"Upserted {collection_name}: "
            f"{start + 1}-{start + len(batch)} / {total}"
        )


def main() -> None:
    products_path = MERGED_DIR / "products_current.parquet"
    reviews_path = MERGED_DIR / "reviews_current.parquet"
    trends_path = MERGED_DIR / "trends_current.parquet"
    feature_base_path = MERGED_DIR / "feature_base.parquet"

    if not products_path.exists():
        raise FileNotFoundError(f"Missing {products_path}")
    if not reviews_path.exists():
        raise FileNotFoundError(f"Missing {reviews_path}")
    if not trends_path.exists():
        raise FileNotFoundError(f"Missing {trends_path}")

    products_df = pd.read_parquet(products_path)
    reviews_df = pd.read_parquet(reviews_path)
    trends_df = pd.read_parquet(trends_path)

    products_df, reviews_df, trends_df = maybe_apply_debug_limits(
        products_df, reviews_df, trends_df
    )

    products_df["product_id"] = products_df["product_id"].astype("string")
    reviews_df["product_id"] = reviews_df["product_id"].astype("string")
    trends_df["product_id"] = trends_df["product_id"].astype("string")

    reviews_df = reduce_reviews(reviews_df)
    trends_df = reduce_trends(trends_df)

    feature_map = build_feature_map(feature_base_path)

    text_embedder = TextEmbedder(
        batch_size=env_int("TEXT_EMBED_BATCH_SIZE", 64),
        timeout=env_int("TEXT_EMBED_TIMEOUT", 1800),
    )
    mm_embedder = MultimodalEmbedder()
    store = QdrantStore()

    product_upsert_batch_size = env_int("QDRANT_UPSERT_BATCH_PRODUCTS", 200)
    review_upsert_batch_size = env_int("QDRANT_UPSERT_BATCH_REVIEWS", 400)
    trend_upsert_batch_size = env_int("QDRANT_UPSERT_BATCH_TRENDS", 400)
    image_upsert_batch_size = env_int("QDRANT_UPSERT_BATCH_IMAGES", 100)
    skip_mm = env_bool("QDRANT_SKIP_MM", True)

    text_dim = len(text_embedder.embed_text("dimension check"))
    mm_dim = mm_embedder.text_dim()

    store.recreate_collection(settings.QDRANT_COLLECTION_PRODUCTS_TEXT, text_dim)
    store.recreate_collection(settings.QDRANT_COLLECTION_REVIEWS_TEXT, text_dim)
    store.recreate_collection(settings.QDRANT_COLLECTION_TRENDS_TEXT, text_dim)
    store.recreate_collection(settings.QDRANT_COLLECTION_PRODUCTS_MM, mm_dim)

    print("Building product texts...")
    product_texts = [build_product_text(row, feature_map) for _, row in products_df.iterrows()]

    print("Embedding product texts...")
    product_vectors = text_embedder.embed_texts(product_texts)

    product_points: list[PointStruct] = []
    for idx, (_, row) in enumerate(products_df.iterrows(), start=1):
        payload = {
            "doc_type": "product",
            "product_id": str(row["product_id"]),
            "title": safe_str(row.get("title", "")),
            "brand": safe_str(row.get("brand", "")),
            "category": safe_str(row.get("category", "")),
            "category_slug": safe_str(row.get("category_slug", "")),
            "category_label": safe_str(row.get("category_label", row.get("category", ""))),
            "price": None if pd.isna(row.get("price")) else float(row.get("price")),
        }
        product_points.append(
            PointStruct(id=idx, vector=product_vectors[idx - 1], payload=payload)
        )

    upsert_in_batches(
        store,
        settings.QDRANT_COLLECTION_PRODUCTS_TEXT,
        product_points,
        batch_size=product_upsert_batch_size,
    )
    print(f"Seeded {len(product_points)} product text points.")

    print("Building review texts...")
    review_texts = [build_review_text(row) for _, row in reviews_df.iterrows()]

    print("Embedding review texts...")
    review_vectors = text_embedder.embed_texts(review_texts)

    review_points: list[PointStruct] = []
    for idx, (_, row) in enumerate(reviews_df.iterrows(), start=1):
        payload = {
            "doc_type": "review",
            "product_id": str(row["product_id"]),
            "review_id": safe_str(row.get("review_id", "")),
            "rating": None if pd.isna(row.get("rating")) else float(row.get("rating")),
            "review_text": safe_str(row.get("review_text", "")),
            "category_slug": safe_str(row.get("category_slug", "")),
            "category_label": safe_str(row.get("category_label", row.get("category", ""))),
        }
        review_points.append(
            PointStruct(id=idx, vector=review_vectors[idx - 1], payload=payload)
        )

    upsert_in_batches(
        store,
        settings.QDRANT_COLLECTION_REVIEWS_TEXT,
        review_points,
        batch_size=review_upsert_batch_size,
    )
    print(f"Seeded {len(review_points)} review text points.")

    trends_df = trends_df[trends_df["product_id"].notna()].copy()

    if trends_df.empty:
        print("No mapped trend rows found; skipping trends_text seeding.")
    else:
        print("Building trend texts...")
        trend_texts = [build_trend_text(row) for _, row in trends_df.iterrows()]

        print("Embedding trend texts...")
        trend_vectors = text_embedder.embed_texts(trend_texts)

        trend_points: list[PointStruct] = []
        for idx, (_, row) in enumerate(trends_df.iterrows(), start=1):
            payload = {
                "doc_type": "trend",
                "product_id": safe_str(row.get("product_id", "")),
                "trend_keyword": safe_str(row.get("trend_keyword", "")),
                "captured_at": safe_str(row.get("captured_at", row.get("week", ""))),
                "trend_index": None if pd.isna(row.get("trend_index")) else float(row.get("trend_index")),
                "trend_change_pct": None if pd.isna(row.get("trend_change_pct")) else float(row.get("trend_change_pct")),
                "category_slug": safe_str(row.get("category_slug", "")),
                "category_label": safe_str(row.get("category_label", row.get("category", ""))),
            }
            trend_points.append(
                PointStruct(id=idx, vector=trend_vectors[idx - 1], payload=payload)
            )

        upsert_in_batches(
            store,
            settings.QDRANT_COLLECTION_TRENDS_TEXT,
            trend_points,
            batch_size=trend_upsert_batch_size,
        )
        print(f"Seeded {len(trend_points)} trend text points.")

    if skip_mm:
        print("Skipping multimodal image seeding because QDRANT_SKIP_MM=true.")
        return

    image_rows = []
    image_paths = []
    for _, row in products_df.iterrows():
        product_id = str(row["product_id"])
        img_path = IMAGE_DIR / f"{product_id}.jpg"
        if img_path.exists():
            image_rows.append(row)
            image_paths.append(img_path)

    if image_paths:
        print("Embedding product images...")
        image_vectors = mm_embedder.embed_images(image_paths)

        image_points: list[PointStruct] = []
        for idx, row in enumerate(image_rows, start=1):
            payload = {
                "doc_type": "product_image",
                "product_id": str(row["product_id"]),
                "title": safe_str(row.get("title", "")),
                "brand": safe_str(row.get("brand", "")),
                "category": safe_str(row.get("category", "")),
                "category_slug": safe_str(row.get("category_slug", "")),
                "category_label": safe_str(row.get("category_label", row.get("category", ""))),
                "image_path": str(IMAGE_DIR / f"{row['product_id']}.jpg"),
            }
            image_points.append(
                PointStruct(id=idx, vector=image_vectors[idx - 1], payload=payload)
            )

        upsert_in_batches(
            store,
            settings.QDRANT_COLLECTION_PRODUCTS_MM,
            image_points,
            batch_size=image_upsert_batch_size,
        )
        print(f"Seeded {len(image_points)} multimodal image points.")
    else:
        print("No local product images found; products_mm collection is empty.")


if __name__ == "__main__":
    main()