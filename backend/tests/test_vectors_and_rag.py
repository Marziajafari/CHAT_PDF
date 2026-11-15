from app.services import embedding_service, rag_service, vector_store
from tests.conftest import PHOTOSYNTHESIS, ROMAN_EMPIRE


def test_embedding_generation():
    vectors = embedding_service.embed_texts(["hello world", "another sentence"])
    assert len(vectors) == 2
    assert len(vectors[0]) == len(vectors[1]) > 100
    assert abs(sum(v * v for v in vectors[0]) - 1.0) < 1e-6  # normalised


def test_vector_storage_and_retrieval(client, upload):
    doc = upload([PHOTOSYNTHESIS])
    hits = vector_store.query(embedding_service.embed_query("chlorophyll absorbs light"), [doc["id"]], 3)
    assert hits and hits[0]["metadata"]["document_id"] == doc["id"]
    assert hits[0]["metadata"]["page_number"] == 1
    assert hits[0]["score"] > 0.12
    client.delete(f"/api/documents/{doc['id']}")


def test_retrieval_filters_by_document(client, upload):
    bio = upload([PHOTOSYNTHESIS], name="bio.pdf")
    history = upload([ROMAN_EMPIRE], name="history.pdf")

    only_history = rag_service.retrieve("emperors and Roman legions", [history["id"]])
    assert only_history and {h["metadata"]["document_id"] for h in only_history} == {history["id"]}

    # the same question limited to the biology document must not return history chunks
    only_bio = rag_service.retrieve("emperors and Roman legions", [bio["id"]], threshold=0.0)
    assert all(h["metadata"]["document_id"] == bio["id"] for h in only_bio)

    both = rag_service.retrieve("emperors and Roman legions", [bio["id"], history["id"]])
    assert both and both[0]["metadata"]["document_id"] == history["id"]
    for d in (bio, history):
        client.delete(f"/api/documents/{d['id']}")


def test_irrelevant_question_returns_nothing(client, upload):
    doc = upload([PHOTOSYNTHESIS])
    assert rag_service.retrieve("zxqv blorptastic", [doc["id"]]) == []
    client.delete(f"/api/documents/{doc['id']}")
