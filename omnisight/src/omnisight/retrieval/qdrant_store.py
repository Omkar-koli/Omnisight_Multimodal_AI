from __future__ import annotations

from typing import Any, List

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from omnisight.settings import settings


class QdrantStore:
    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.QDRANT_URL)

    def recreate_collection(self, collection_name: str, vector_size: int) -> None:
        self.client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def upsert_points(self, collection_name: str, points: List[PointStruct]) -> None:
        self.client.upsert(collection_name=collection_name, points=points)

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
    ) -> list[Any]:
        response = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return response.points