from fastapi import APIRouter
from sqlalchemy import func, select, text

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import Document
from app.services import embedding_service, ollama_service, vector_store

router = APIRouter(prefix="/api", tags=["system"])
VERSION = "1.0.0"


@router.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name, "version": VERSION}


@router.get("/system/status")
def system_status():
    database = {"status": "error", "documents": 0}
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            database = {"status": "ok", "documents": db.scalar(select(func.count()).select_from(Document)) or 0}
    except Exception:
        pass
    vectors = {"status": "error", "chunks": 0}
    try:
        vectors = {"status": "ok", "chunks": vector_store.count()}
    except Exception:
        pass
    return {
        "app": settings.app_name,
        "version": VERSION,
        "backend": "ok",
        "ollama": ollama_service.status(),
        "embeddings": embedding_service.status(),
        "database": database,
        "vector_store": vectors,
        "config": {
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "top_k": settings.top_k,
            "relevance_threshold": settings.relevance_threshold,
            "max_upload_mb": settings.max_upload_mb,
        },
    }
