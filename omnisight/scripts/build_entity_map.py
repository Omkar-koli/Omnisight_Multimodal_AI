from __future__ import annotations

from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PRODUCTS_PATH = PROCESSED_DIR / "products.parquet"
TRENDS_PATH = PROCESSED_DIR / "trends.parquet"
REDDIT_PATH = PROCESSED_DIR / "reddit_mentions.parquet"
UCI_PATH = PROCESSED_DIR / "transactions_uci.parquet"


def norm(s: str) -> str:
    return " ".join(str(s).lower().replace("-", " ").replace("/", " ").split())


def best_match(term: str, candidates: list[tuple[str, str]]) -> tuple[str | None, float]:
    best_id = None
    best_score = 0.0
    for product_id, title in candidates:
        score = fuzz.token_set_ratio(norm(term), norm(title))
        if score > best_score:
            best_score = float(score)
            best_id = product_id
    return best_id, best_score


def main() -> None:
    products_df = pd.read_parquet(PRODUCTS_PATH)
    candidates = [(str(r["product_id"]), str(r["title"])) for _, r in products_df.iterrows()]

    rows = []

    if TRENDS_PATH.exists():
        trends_df = pd.read_parquet(TRENDS_PATH)
        for keyword in trends_df["trend_keyword"].dropna().astype(str).unique():
            matched_id, score = best_match(keyword, candidates)
            rows.append(
                {
                    "entity_id": f"trend::{keyword}",
                    "entity_name": keyword,
                    "category": "unknown",
                    "amazon_product_id": matched_id,
                    "trend_keyword": keyword,
                    "reddit_query": pd.NA,
                    "uci_description": pd.NA,
                    "match_score": score,
                    "match_method": "fuzzy_title_match",
                }
            )

    if REDDIT_PATH.exists():
        reddit_df = pd.read_parquet(REDDIT_PATH)
        for query in reddit_df["query"].dropna().astype(str).unique():
            matched_id, score = best_match(query, candidates)
            rows.append(
                {
                    "entity_id": f"reddit::{query}",
                    "entity_name": query,
                    "category": "unknown",
                    "amazon_product_id": matched_id,
                    "trend_keyword": pd.NA,
                    "reddit_query": query,
                    "uci_description": pd.NA,
                    "match_score": score,
                    "match_method": "fuzzy_title_match",
                }
            )

    if UCI_PATH.exists():
        uci_df = pd.read_parquet(UCI_PATH)
        if "description" in uci_df.columns:
            for desc in uci_df["description"].dropna().astype(str).unique()[:500]:
                matched_id, score = best_match(desc, candidates)
                rows.append(
                    {
                        "entity_id": f"uci::{desc}",
                        "entity_name": desc,
                        "category": "unknown",
                        "amazon_product_id": matched_id,
                        "trend_keyword": pd.NA,
                        "reddit_query": pd.NA,
                        "uci_description": desc,
                        "match_score": score,
                        "match_method": "fuzzy_title_match",
                    }
                )

    entity_map_df = pd.DataFrame(rows).drop_duplicates(subset=["entity_id"])
    entity_map_df.to_parquet(PROCESSED_DIR / "entity_map.parquet", index=False)
    print("Saved entity_map.parquet")


if __name__ == "__main__":
    main()