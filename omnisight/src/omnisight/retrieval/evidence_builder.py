from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd

from omnisight.embeddings.multimodal_embedder import MultimodalEmbedder
from omnisight.embeddings.text_embedder import TextEmbedder
from omnisight.retrieval.qdrant_store import QdrantStore
from omnisight.settings import settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MERGED_DIR = PROJECT_ROOT / "data" / "processed" / "merged"


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)


def load_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


class EvidenceBuilder:
    def __init__(self) -> None:
        self.text_embedder = TextEmbedder()
        self.mm_embedder = MultimodalEmbedder()
        self.store = QdrantStore()

        self.products_path = MERGED_DIR / "products_current.parquet"
        self.recommendations_path = MERGED_DIR / "recommendations.parquet"

        self.products_df = load_table(self.products_path)
        self.recommendations_df = load_table(self.recommendations_path)

        if not self.products_df.empty and "product_id" in self.products_df.columns:
            self.products_df["product_id"] = self.products_df["product_id"].astype("string")

        if not self.recommendations_df.empty and "product_id" in self.recommendations_df.columns:
            self.recommendations_df["product_id"] = self.recommendations_df["product_id"].astype("string")

    def _get_product_row(self, product_id: str) -> dict:
        if self.products_df.empty or "product_id" not in self.products_df.columns:
            return {}

        product_id = str(product_id).strip()

        match_df = self.products_df[
            self.products_df["product_id"].astype(str).str.strip() == product_id
        ]

        if match_df.empty:
            return {}

        return match_df.iloc[0].to_dict()

    def _get_rule_row(self, product_id: str) -> dict:
        if self.recommendations_df.empty or "product_id" not in self.recommendations_df.columns:
            return {}

        product_id = str(product_id).strip()

        match_df = self.recommendations_df[
            self.recommendations_df["product_id"].astype(str).str.strip() == product_id
        ]

        if match_df.empty:
            return {}

        return match_df.iloc[0].to_dict()

    def _filter_hits_by_product(self, hits, product_id: str, top_k: int = 3):
        out = []
        target = safe_str(product_id).strip()

        for hit in hits:
            payload = hit.payload or {}
            hit_product_id = safe_str(payload.get("product_id")).strip()

            if hit_product_id == target:
                out.append(hit)

            if len(out) >= top_k:
                break

        return out

    def build(self, product_id: str) -> Dict[str, Any]:
        product_id = str(product_id).strip()

        product_row = self._get_product_row(product_id)
        rule_row = self._get_rule_row(product_id)

        if not product_row:
            raise ValueError(
                f"Product not found for product_id={product_id} "
                f"in {self.products_path}"
            )

        query_parts = [
            safe_str(product_row.get("title")),
            safe_str(product_row.get("brand")),
            safe_str(product_row.get("category_label", product_row.get("category"))),
            safe_str(product_row.get("description")),
        ]
        query_text = " | ".join([x for x in query_parts if x])

        text_query_vec = self.text_embedder.embed_text(query_text)
        mm_query_vec = self.mm_embedder.embed_texts([query_text])[0]

        review_hits_all = self.store.search(
            settings.QDRANT_COLLECTION_REVIEWS_TEXT,
            text_query_vec,
            limit=15,
        )
        trend_hits_all = self.store.search(
            settings.QDRANT_COLLECTION_TRENDS_TEXT,
            text_query_vec,
            limit=15,
        )
        image_hits_all = self.store.search(
            settings.QDRANT_COLLECTION_PRODUCTS_MM,
            mm_query_vec,
            limit=10,
        )

        review_hits = self._filter_hits_by_product(review_hits_all, product_id, top_k=3)
        trend_hits = self._filter_hits_by_product(trend_hits_all, product_id, top_k=3)
        image_hits = self._filter_hits_by_product(image_hits_all, product_id, top_k=1)

        review_evidence = []
        for hit in review_hits:
            payload = hit.payload or {}
            review_evidence.append(
                {
                    "review_id": safe_str(payload.get("review_id")),
                    "rating": payload.get("rating"),
                    "review_text": safe_str(payload.get("review_text")),
                    "score": getattr(hit, "score", None),
                }
            )

        trend_evidence = []
        for hit in trend_hits:
            payload = hit.payload or {}
            trend_evidence.append(
                {
                    "trend_keyword": safe_str(payload.get("trend_keyword")),
                    "captured_at": safe_str(payload.get("captured_at", payload.get("week"))),
                    "trend_index": payload.get("trend_index"),
                    "trend_change_pct": payload.get("trend_change_pct"),
                    "score": getattr(hit, "score", None),
                }
            )

        image_evidence = []
        for hit in image_hits:
            payload = hit.payload or {}
            image_evidence.append(
                {
                    "image_path": safe_str(payload.get("image_path")),
                    "title": safe_str(payload.get("title")),
                    "score": getattr(hit, "score", None),
                }
            )

        return {
            "product": product_row,
            "rules": rule_row,
            "reviews": review_evidence,
            "trends": trend_evidence,
            "images": image_evidence,
        }