"""ChromaDB wrapper: one persistent collection holding every chunk of every document."""
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings

COLLECTION_NAME = "studymate_chunks"
_WRITE_BATCH = 128


@lru_cache(maxsize=1)
def _collection():
    client = chromadb.PersistentClient(
        path=str(settings.chroma_dir),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def add_chunks(
    document_id: str,
    filename: str,
    chunks: Sequence[Dict[str, Any]],
    embeddings: Sequence[Sequence[float]],
) -> None:
    col = _collection()
    for i in range(0, len(chunks), _WRITE_BATCH):
        part = chunks[i : i + _WRITE_BATCH]
        col.upsert(
            ids=[f"{document_id}-{c['chunk_index']}" for c in part],
            documents=[c["text"] for c in part],
            embeddings=[list(e) for e in embeddings[i : i + _WRITE_BATCH]],
            metadatas=[
                {
                    "document_id": document_id,
                    "filename": filename,
                    "page_number": int(c["page_number"]),
                    "chunk_index": int(c["chunk_index"]),
                }
                for c in part
            ],
        )


def query(
    embedding: Sequence[float], document_ids: Optional[Sequence[str]], top_k: int
) -> List[Dict[str, Any]]:
    """Semantic search. Returns chunks with `score` = cosine similarity (1.0 = identical)."""
    col = _collection()
    if col.count() == 0:
        return []
    where: Optional[Dict[str, Any]] = None
    if document_ids:
        ids = list(document_ids)
        where = {"document_id": ids[0]} if len(ids) == 1 else {"document_id": {"$in": ids}}
    res = col.query(query_embeddings=[list(embedding)], n_results=top_k, where=where)
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]
    return [
        {"text": t, "metadata": m, "score": round(1.0 - float(d), 4)}
        for t, m, d in zip(docs, metas, dists)
    ]


def get_document_chunks(document_id: str) -> List[Dict[str, Any]]:
    """All chunks of one document in reading order (used for summaries, quizzes, flashcards)."""
    res = _collection().get(where={"document_id": document_id}, include=["documents", "metadatas"])
    items = [
        {"text": t, "page_number": m["page_number"], "chunk_index": m["chunk_index"]}
        for t, m in zip(res["documents"], res["metadatas"])
    ]
    items.sort(key=lambda c: c["chunk_index"])
    return items


def delete_document(document_id: str) -> None:
    _collection().delete(where={"document_id": document_id})


def count() -> int:
    return _collection().count()


def count_for_document(document_id: str) -> int:
    return len(_collection().get(where={"document_id": document_id}, include=[])["ids"])
