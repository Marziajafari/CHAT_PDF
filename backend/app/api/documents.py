import re
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Document
from app.schemas.schemas import DocumentOut
from app.services import document_service, pdf_service
from app.services.errors import PdfError

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _safe_display_name(raw: Optional[str]) -> str:
    """Keep only the file name (no folders), drop control/odd characters, limit length."""
    name = Path((raw or "document.pdf").replace("\\", "/")).name
    name = re.sub(r"[^\w\-. ()]", "_", name).strip(" .") or "document.pdf"
    return name[:200]


@router.post("/upload", response_model=DocumentOut, status_code=202)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    display_name = _safe_display_name(file.filename)
    if not display_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are accepted.")

    # Stored under a random name, so user-supplied names can never touch the file system.
    stored_name = f"{uuid.uuid4().hex}.pdf"
    path = settings.upload_dir / stored_name
    size = 0
    header = b""
    try:
        with open(path, "wb") as out:
            while True:
                block = file.file.read(1024 * 1024)
                if not block:
                    break
                if not header:
                    header = block[:1024]
                size += len(block)
                if size > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File is larger than the {settings.max_upload_mb} MB limit.",
                    )
                out.write(block)

        if size == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")
        if not pdf_service.has_pdf_header(header):
            raise HTTPException(status_code=400, detail="This file is not a real PDF (invalid file content).")
        try:
            page_count = pdf_service.inspect_pdf(path)
        except PdfError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
    except HTTPException:
        path.unlink(missing_ok=True)
        raise
    except Exception:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="The file could not be saved.") from None

    doc = Document(
        filename=stored_name,
        original_filename=display_name,
        file_path=str(path),
        file_size=size,
        page_count=page_count,
        processing_status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    background_tasks.add_task(document_service.process_document, doc.id)
    return doc


@router.get("", response_model=List[DocumentOut])
def list_documents(q: Optional[str] = None, db: Session = Depends(get_db)):
    stmt = select(Document).order_by(Document.upload_date.desc())
    if q:
        stmt = stmt.where(Document.original_filename.ilike(f"%{q}%"))
    return db.scalars(stmt).all()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    document_service.delete_document(db, doc)
    return Response(status_code=204)
