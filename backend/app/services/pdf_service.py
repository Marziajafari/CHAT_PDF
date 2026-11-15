"""PDF validation and page-by-page text extraction with PyMuPDF."""
from pathlib import Path
from typing import List, Tuple

try:  # PyMuPDF >= 1.24.3 exposes `pymupdf`; older versions only `fitz`
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore

from app.services.errors import PdfError
from app.services.text_utils import clean_text


def has_pdf_header(data: bytes) -> bool:
    """Real PDFs start with '%PDF-' (some have a few junk bytes before it)."""
    return b"%PDF-" in data[:1024]


def inspect_pdf(path: Path) -> int:
    """Open the file and return its page count, or raise PdfError with a friendly message."""
    try:
        with fitz.open(str(path)) as doc:
            if doc.needs_pass or doc.is_encrypted:
                raise PdfError("This PDF is password-protected. Remove the password and upload it again.")
            if doc.page_count == 0:
                raise PdfError("This PDF has no pages.")
            return doc.page_count
    except PdfError:
        raise
    except Exception:
        raise PdfError("This file is not a valid PDF or it is corrupted.") from None


def extract_pages(path: Path) -> List[Tuple[int, str]]:
    """Return [(page_number starting at 1, cleaned_text), ...] for pages that contain text."""
    pages: List[Tuple[int, str]] = []
    try:
        with fitz.open(str(path)) as doc:
            if doc.needs_pass:
                raise PdfError("This PDF is password-protected.")
            for index, page in enumerate(doc):
                text = clean_text(page.get_text("text"))
                if text:
                    pages.append((index + 1, text))
    except PdfError:
        raise
    except Exception:
        raise PdfError("The PDF could not be read.") from None
    return pages
