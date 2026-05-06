from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np
from PIL import Image
from sentence_transformers import SentenceTransformer

from omnisight.settings import settings


class MultimodalEmbedder:
    def __init__(self) -> None:
        self.model_name = settings.MM_EMBED_MODEL
        self.model = SentenceTransformer(self.model_name)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_images(self, image_paths: List[Path]) -> List[List[float]]:
        images = [Image.open(path).convert("RGB") for path in image_paths]
        embeddings = self.model.encode(
            images,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def text_dim(self) -> int:
        vec = self.embed_texts(["dimension check"])
        return len(vec[0])