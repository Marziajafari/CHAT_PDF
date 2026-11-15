from pathlib import Path

from app.db.database import SessionLocal
from app.db.models import Document
from app.services import pdf_service, vector_store
from tests.conftest import PHOTOSYNTHESIS, make_pdf


def test_rejects_non_pdf_extension(client):
    r = client.post("/api/documents/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_rejects_fake_pdf_content(client):
    r = client.post("/api/documents/upload", files={"file": ("fake.pdf", b"this is not a pdf at all", "application/pdf")})
    assert r.status_code == 400
    assert "PDF" in r.json()["detail"]


def test_rejects_corrupted_pdf(client):
    broken = b"%PDF-1.4\n" + b"garbage" * 50
    r = client.post("/api/documents/upload", files={"file": ("broken.pdf", broken, "application/pdf")})
    assert r.status_code == 400


def test_rejects_empty_file(client):
    r = client.post("/api/documents/upload", files={"file": ("empty.pdf", b"", "application/pdf")})
    assert r.status_code == 400


def test_path_traversal_filename_is_neutralised(client, upload):
    doc = upload([PHOTOSYNTHESIS], name="../../etc/evil.pdf")
    assert "/" not in doc["original_filename"] and ".." not in doc["original_filename"]
    client.delete(f"/api/documents/{doc['id']}")


def test_valid_upload_processes_and_is_listed(client, upload):
    doc = upload([PHOTOSYNTHESIS, "Second page text about leaves and roots."])
    detail = client.get(f"/api/documents/{doc['id']}").json()
    assert detail["processing_status"] == "ready"
    assert detail["page_count"] == 2
    assert detail["chunk_count"] >= 2
    assert doc["id"] in [d["id"] for d in client.get("/api/documents").json()]
    assert vector_store.count_for_document(doc["id"]) == detail["chunk_count"]
    client.delete(f"/api/documents/{doc['id']}")


def test_search_filter(client, upload):
    doc = upload([PHOTOSYNTHESIS], name="biology-unique-name.pdf")
    found = client.get("/api/documents", params={"q": "unique-name"}).json()
    assert [d["id"] for d in found] == [doc["id"]]
    client.delete(f"/api/documents/{doc['id']}")


def test_pdf_without_text_is_marked_failed(client):
    import tests.conftest as c

    pdf = c.fitz.open()
    pdf.new_page()  # blank page: nothing to extract
    data = pdf.tobytes()
    r = client.post("/api/documents/upload", files={"file": ("blank.pdf", data, "application/pdf")})
    assert r.status_code == 202
    detail = client.get(f"/api/documents/{r.json()['id']}").json()
    assert detail["processing_status"] == "failed"
    assert "text" in detail["error_message"].lower()


def test_extraction_is_page_aware(tmp_path):
    path = tmp_path / "x.pdf"
    path.write_bytes(make_pdf(["First page alpha text.", "Second page beta text."]))
    pages = pdf_service.extract_pages(Path(path))
    assert [p for p, _ in pages] == [1, 2]
    assert "alpha" in pages[0][1] and "beta" in pages[1][1]


def test_delete_removes_sqlite_row_file_and_vectors(client, upload):
    doc = upload([PHOTOSYNTHESIS])
    with SessionLocal() as db:
        file_path = Path(db.get(Document, doc["id"]).file_path)
    assert file_path.exists()
    assert vector_store.count_for_document(doc["id"]) > 0

    assert client.delete(f"/api/documents/{doc['id']}").status_code == 204
    assert client.get(f"/api/documents/{doc['id']}").status_code == 404
    assert not file_path.exists()
    assert vector_store.count_for_document(doc["id"]) == 0
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 404


def test_data_persists_in_a_new_database_session(client, upload):
    doc = upload([PHOTOSYNTHESIS])
    with SessionLocal() as fresh_session:  # simulates reading after a restart
        row = fresh_session.get(Document, doc["id"])
        assert row is not None and row.processing_status == "ready"
    client.delete(f"/api/documents/{doc['id']}")
