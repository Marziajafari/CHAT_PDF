"""Shared helpers for routes."""
from typing import List, Sequence

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import Document


def get_ready_documents(db: Session, ids: Sequence[str]) -> List[Document]:
    """Return the documents or raise 404 (unknown) / 409 (still processing or failed)."""
    docs = []
    for doc_id in dict.fromkeys(ids):  # de-duplicate, keep order
        doc = db.get(Document, doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        if doc.processing_status != "ready":
            raise HTTPException(
                status_code=409,
                detail=f"'{doc.original_filename}' is not ready yet (status: {doc.processing_status}).",
            )
        docs.append(doc)
    return docs
