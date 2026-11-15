from tests.conftest import PHOTOSYNTHESIS


def test_chat_returns_answer_with_sources_and_saves_history(client, upload, fake_ollama):
    doc = upload([PHOTOSYNTHESIS], name="biology.pdf")
    r = client.post("/api/chat", json={"question": "chlorophyll absorbs light from sunlight in photosynthesis", "document_ids": [doc["id"]]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answer"].startswith("Mock answer")
    assert body["sources"][0]["filename"] == "biology.pdf"
    assert body["sources"][0]["page_number"] == 1
    assert body["info"]["grounded"] is True

    # the prompt really contains the retrieved context and the grounding instruction
    sent = fake_ollama[-1]["messages"]
    assert "StudyMate AI" in sent[0]["content"]
    assert "Never refuse just because the source is a file" in sent[0]["content"]
    assert "chlorophyll" in sent[-1]["content"].lower()
    assert "Photosynthesis is the process" in sent[-1]["content"]
    assert "biology.pdf" not in sent[-1]["content"]

    chat = client.get(f"/api/chats/{body['chat_id']}").json()
    assert [m["role"] for m in chat["messages"]] == ["user", "assistant"]
    assert chat["messages"][1]["sources"][0]["page_number"] == 1
    assert body["chat_id"] in [c["id"] for c in client.get("/api/chats").json()]

    # follow-up in the same conversation sends previous turns as history
    r2 = client.post("/api/chat", json={"question": "Explain chlorophyll again", "chat_id": body["chat_id"], "document_ids": [doc["id"]]})
    assert r2.json()["chat_id"] == body["chat_id"]
    assert len(fake_ollama[-1]["messages"]) >= 4

    assert client.delete(f"/api/chats/{body['chat_id']}").status_code == 204
    assert client.get(f"/api/chats/{body['chat_id']}").status_code == 404
    client.delete(f"/api/documents/{doc['id']}")


def test_unanswerable_question_is_handled_honestly_without_calling_the_model(client, upload, fake_ollama):
    doc = upload([PHOTOSYNTHESIS])
    r = client.post("/api/chat", json={"question": "zxqv blorptastic", "document_ids": [doc["id"]]})
    assert r.status_code == 200
    body = r.json()
    assert "does not provide enough information" in body["answer"]
    assert body["sources"] == []
    assert body["info"]["llm_called"] is False
    assert fake_ollama == []
    client.delete(f"/api/documents/{doc['id']}")


def test_chat_validation_and_errors(client):
    assert client.post("/api/chat", json={"question": ""}).status_code == 422
    assert client.post("/api/chat", json={"question": "hi", "document_ids": ["missing"]}).status_code == 404
    assert client.post("/api/chat", json={"question": "hi", "chat_id": "missing"}).status_code == 404


def test_ollama_down_gives_clear_503(client, upload, monkeypatch):
    from app.services import ollama_service
    from app.services.errors import OllamaError

    def broken(*args, **kwargs):
        raise OllamaError("Cannot reach Ollama. Start it with `ollama serve`.")

    monkeypatch.setattr(ollama_service, "chat", broken)
    doc = upload([PHOTOSYNTHESIS])
    r = client.post("/api/chat", json={"question": "chlorophyll light photosynthesis", "document_ids": [doc["id"]]})
    assert r.status_code == 503
    assert "Ollama" in r.json()["detail"]
    client.delete(f"/api/documents/{doc['id']}")
