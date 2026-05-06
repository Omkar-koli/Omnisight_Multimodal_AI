from __future__ import annotations

import math
import os
from typing import List, Optional

import requests


class TextEmbedder:
    def __init__(self, batch_size: Optional[int] = 32, timeout: int = 900, log_every: int = 20):
        self.batch_size = batch_size
        self.timeout = timeout
        self.log_every = log_every

        base_url = (
            os.getenv("OLLAMA_API_BASE")
            or os.getenv("OLLAMA_BASE_URL")
            or os.getenv("LLM_BASE_URL")
            or "http://localhost:11434"
        ).rstrip("/")

        if base_url.endswith("/v1"):
            base_url = base_url[:-3]

        self.base_url = base_url
        self.model = (
            os.getenv("OLLAMA_EMBED_MODEL")
            or os.getenv("TEXT_EMBED_MODEL")
            or "embeddinggemma"
        )

    def _embed_batch(self, texts: List[str]) -> List[list[float]]:
        response = requests.post(
            f"{self.base_url}/api/embed",
            json={
                "model": self.model,
                "input": texts,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()

        embeddings = payload.get("embeddings") or payload.get("embedding")
        if not embeddings:
            raise ValueError(f"No embeddings returned from Ollama. Response: {payload}")

        return embeddings

    def embed_texts(self, texts: List[str]) -> List[list[float]]:
        if not texts:
            return []

        # One-shot mode if batch_size is None or <= 0
        if not self.batch_size or self.batch_size <= 0:
            print(f"Embedding all {len(texts)} texts in one request...")
            return self._embed_batch(texts)

        all_vectors: List[list[float]] = []
        total_batches = math.ceil(len(texts) / self.batch_size)

        for batch_idx, start in enumerate(range(0, len(texts), self.batch_size), start=1):
            batch = texts[start:start + self.batch_size]

            if batch_idx == 1 or batch_idx % self.log_every == 0 or batch_idx == total_batches:
                print(
                    f"Embedding batch {batch_idx}/{total_batches} "
                    f"(items {start} to {start + len(batch) - 1})..."
                )

            batch_vectors = self._embed_batch(batch)
            all_vectors.extend(batch_vectors)

        return all_vectors

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]