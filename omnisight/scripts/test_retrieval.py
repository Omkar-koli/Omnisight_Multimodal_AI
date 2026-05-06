from __future__ import annotations

from omnisight.embeddings.multimodal_embedder import MultimodalEmbedder
from omnisight.embeddings.text_embedder import TextEmbedder
from omnisight.retrieval.qdrant_store import QdrantStore
from omnisight.settings import settings


def print_hits(title: str, hits) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    if not hits:
        print("No hits.")
        print("-" * 70)
        return

    for idx, hit in enumerate(hits, start=1):
        print(f"{idx}. score={hit.score:.4f}")
        print(hit.payload)
        print("-" * 70)


def infer_category_slug(query: str) -> str | None:
    q = query.lower()

    home_keywords = [
        "home and kitchen",
        "kitchen",
        "home",
        "storage",
        "organizer",
        "table",
        "bedding",
        "decor",
        "cookware",
        "bathroom",
        "placemat",
        "soap dispenser",
        "pillowcase",
    ]
    beauty_keywords = [
        "beauty and personal care",
        "beauty",
        "skincare",
        "skin care",
        "makeup",
        "hair",
        "wig",
        "nail",
        "eyelash",
        "sunscreen",
        "perfume",
        "cosmetic",
        "lipstick",
    ]
    toy_keywords = [
        "toys and games",
        "toy",
        "games",
        "kids",
        "collectible",
        "doll",
        "jenga",
        "puzzle",
        "monster truck",
        "water gun",
        "building blocks",
    ]

    if any(k in q for k in home_keywords):
        return "home_and_kitchen"
    if any(k in q for k in beauty_keywords):
        return "beauty_and_personal_care"
    if any(k in q for k in toy_keywords):
        return "toys_and_games"

    return None


def filter_hits_by_category(hits, category_slug: str | None, limit: int = 5):
    if not category_slug:
        return hits[:limit]

    filtered = [
        hit for hit in hits
        if str(hit.payload.get("category_slug", "")).strip().lower() == category_slug
    ]

    if filtered:
        return filtered[:limit]

    return hits[:limit]


def search_with_optional_category(
    store: QdrantStore,
    collection_name: str,
    query_vector,
    category_slug: str | None,
    limit: int = 5,
    overfetch: int = 30,
):
    hits = store.search(
        collection_name,
        query_vector,
        limit=overfetch,
    )
    return filter_hits_by_category(hits, category_slug, limit=limit)


def main() -> None:
    query = input("Enter your search query: ").strip()
    if not query:
        query = "viral collectible toy with strong trend growth and mixed reviews"

    forced_category = input(
        "Optional category filter [toys_and_games / home_and_kitchen / beauty_and_personal_care] (press Enter to auto-detect): "
    ).strip().lower()

    category_slug = forced_category or infer_category_slug(query)

    print(f"\nQuery: {query}")
    print(f"Category filter: {category_slug or 'none'}")

    text_embedder = TextEmbedder()
    mm_embedder = MultimodalEmbedder()
    store = QdrantStore()

    text_query_vec = text_embedder.embed_text(query)
    mm_query_vec = mm_embedder.embed_texts([query])[0]

    product_hits = search_with_optional_category(
        store,
        settings.QDRANT_COLLECTION_PRODUCTS_TEXT,
        text_query_vec,
        category_slug,
        limit=5,
        overfetch=30,
    )
    review_hits = search_with_optional_category(
        store,
        settings.QDRANT_COLLECTION_REVIEWS_TEXT,
        text_query_vec,
        category_slug,
        limit=5,
        overfetch=30,
    )
    trend_hits = search_with_optional_category(
        store,
        settings.QDRANT_COLLECTION_TRENDS_TEXT,
        text_query_vec,
        category_slug,
        limit=5,
        overfetch=30,
    )
    image_hits = search_with_optional_category(
        store,
        settings.QDRANT_COLLECTION_PRODUCTS_MM,
        mm_query_vec,
        category_slug,
        limit=5,
        overfetch=30,
    )

    print_hits("PRODUCT TEXT HITS", product_hits)
    print_hits("REVIEW TEXT HITS", review_hits)
    print_hits("TREND TEXT HITS", trend_hits)
    print_hits("PRODUCT IMAGE HITS", image_hits)


if __name__ == "__main__":
    main()