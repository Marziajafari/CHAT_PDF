"""Local text embeddings. Loaded lazily so the API starts fast and uses little RAM."""
import hashlib
import math
import re
from functools import lru_cache
from typing import List

from app.core.config import settings


class SentenceTransformerEmbedder:
    """all-MiniLM-L6-v2 (~90 MB, 384 dimensions, runs on CPU)."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            try:  # use the local cache only: no repeated downloads / network calls
                self._model = SentenceTransformer(self.model_name, device="cpu", local_files_only=True)
            except Exception:  # first run: download once, then it is cached on disk
                self._model = SentenceTransformer(self.model_name, device="cpu")
        return self._model

    def embed(self, texts: List[str]) -> List[List[float]]:
        model = self._load()
        vectors = model.encode(
            texts,
            batch_size=settings.embed_batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()


class HashEmbedder:
    """Deterministic bag-of-words embedder. ONLY for automated tests (no model download)."""

    dim = 1024
    loaded = True

    def __init__(self, model_name: str = "hash"):
        self.model_name = "hash-test-embedder"

    def embed(self, texts: List[str]) -> List[List[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for token in re.findall(r"\w+", text.lower()):
                digest = hashlib.md5(token.encode("utf-8")).digest()
                idx = int.from_bytes(digest[:4], "little") % self.dim
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vec[idx] += sign
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


@lru_cache(maxsize=1)
def get_embedder():
    if settings.embedding_backend == "hash":
        return HashEmbedder()
    return SentenceTransformerEmbedder(settings.embedding_model)


def embed_texts(texts: List[str]) -> List[List[float]]:
    return get_embedder().embed(texts)


def embed_query(query: str) -> List[float]:
    return get_embedder().embed([query])[0]


def status() -> dict:
    embedder = get_embedder()
    return {
        "backend": settings.embedding_backend,
        "model": embedder.model_name,
        "loaded": bool(embedder.loaded),
    }
