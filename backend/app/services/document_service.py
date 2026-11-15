"""Document lifecycle: background processing (extract -> chunk -> embed -> store) and deletion."""
import logging
from pathlib import Path

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import Document
from app.services import embedding_service, pdf_service, vector_store
from app.services.errors import PdfError
from app.services.text_utils import chunk_pages

log = logging.getLogger("studymate.documents")


def _fail(db, doc: Document, message: str) -> None:
    doc.processing_status = "failed"
    doc.error_message = message[:500]
    db.commit()


def process_document(document_id: str) -> None:
    """Runs after the upload response is sent (FastAPI BackgroundTasks)."""
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc is None:
            return
        try:
            pages = pdf_service.extract_pages(Path(doc.file_path))
            chunks = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)
            if not chunks:
                _fail(db, doc, "No extractable text found. Scanned PDFs (images only) are not supported.")
                return
            batch = settings.embed_batch_size
            for i in range(0, len(chunks), batch):  # embed in small batches to keep RAM low
                part = chunks[i : i + batch]
                vectors = embedding_service.embed_texts([c["text"] for c in part])
                vector_store.add_chunks(doc.id, doc.original_filename, part, vectors)
            doc.chunk_count = len(chunks)
            doc.processing_status = "ready"
            doc.error_message = None
            db.commit()
        except PdfError as exc:
            vector_store.delete_document(document_id)
            _fail(db, doc, str(exc))
        except Exception:
            log.exception("Processing failed for document %s", document_id)
            try:
                vector_store.delete_document(document_id)
            except Exception:
                pass
            _fail(db, doc, "Processing failed. Check the backend log for details.")
    finally:
        db.close()


def delete_document(db, doc: Document) -> None:
    """Remove vectors, the stored file and the SQLite rows (quizzes/flashcards cascade)."""
    vector_store.delete_document(doc.id)
    try:
        Path(doc.file_path).unlink(missing_ok=True)
    except OSError:
        log.warning("Could not delete file %s", doc.file_path)
    db.delete(doc)
    db.commit()
