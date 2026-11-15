import json

from app.services import ollama_service
from tests.conftest import PHOTOSYNTHESIS, ROMAN_EMPIRE


def test_summarize(client, upload, fake_ollama):
    doc = upload([PHOTOSYNTHESIS])
    r = client.post("/api/ai/summarize", json={"document_id": doc["id"], "mode": "detailed"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"] and body["key_concepts"] and body["definitions"][0]["term"] == "Chlorophyll"
    assert body["exam_notes"]
    client.delete(f"/api/documents/{doc['id']}")


def test_summarize_large_document_uses_sections(client, upload, fake_ollama):
    long_pages = [("Sentence about topic number %d. " % i) * 60 for i in range(6)]
    doc = upload(long_pages)
    body = client.post("/api/ai/summarize", json={"document_id": doc["id"], "mode": "short"}).json()
    assert body["sections_total"] >= 1
    assert len(fake_ollama) <= 4  # batched section summaries plus one final structured summary
    client.delete(f"/api/documents/{doc['id']}")


def test_quiz_generation_hides_answers_and_scores(client, upload, fake_ollama):
    doc = upload([PHOTOSYNTHESIS, ROMAN_EMPIRE])
    r = client.post("/api/ai/generate-quiz", json={"document_id": doc["id"], "difficulty": "easy", "num_questions": 2})
    assert r.status_code == 200, r.text
    quiz = r.json()
    assert len(quiz["questions"]) == 2
    assert len(fake_ollama) == 1
    text = json.dumps(quiz)
    assert "correct_index" not in text and "explanation" not in text  # no answers before submitting
    assert all(len(q["options"]) == 4 for q in quiz["questions"])

    wrong_all = client.post("/api/ai/submit-quiz", json={"quiz_id": quiz["quiz_id"], "answers": [None, None]})
    assert wrong_all.json()["score"] == 0

    # find the right answers from the (now revealed) result and retake the same quiz
    results = wrong_all.json()["results"]
    right = [r_["correct_index"] for r_ in results]
    retake = client.post("/api/ai/submit-quiz", json={"quiz_id": quiz["quiz_id"], "answers": right}).json()
    assert retake["score"] == 2 and retake["total"] == 2
    assert retake["quiz_id"] != quiz["quiz_id"]  # stored as a new attempt
    assert all(x["explanation"] for x in retake["results"])

    history = client.get("/api/ai/quiz-history").json()
    assert len(history) >= 2
    client.delete(f"/api/documents/{doc['id']}")


def test_quiz_submit_validation(client):
    assert client.post("/api/ai/submit-quiz", json={"quiz_id": "nope", "answers": []}).status_code == 404


def test_malformed_model_output_is_rejected(client, upload, monkeypatch):
    def bad(messages, json_mode=False, **kw):
        return json.dumps(
            {"questions": [{"question": "Only two options here?", "options": ["a", "b"], "correct_index": 5, "explanation": "x"}]}
        )

    monkeypatch.setattr(ollama_service, "chat", bad)
    doc = upload([PHOTOSYNTHESIS])
    r = client.post("/api/ai/generate-quiz", json={"document_id": doc["id"], "difficulty": "easy", "num_questions": 2})
    assert r.status_code == 502
    client.delete(f"/api/documents/{doc['id']}")


def test_non_json_model_output_is_rejected(client, upload, monkeypatch):
    monkeypatch.setattr(ollama_service, "chat", lambda *a, **k: "I am sorry, here is some prose.")
    doc = upload([PHOTOSYNTHESIS])
    assert client.post("/api/ai/generate-flashcards", json={"document_id": doc["id"], "num_cards": 3}).status_code == 502
    client.delete(f"/api/documents/{doc['id']}")


def test_flashcards_and_progress(client, upload, fake_ollama):
    doc = upload([PHOTOSYNTHESIS, ROMAN_EMPIRE])
    r = client.post("/api/ai/generate-flashcards", json={"document_id": doc["id"], "num_cards": 4})
    assert r.status_code == 200, r.text
    fs = r.json()
    assert len(fs["cards"]) == 4
    assert fs["cards"][0]["source_page"] in (1, 2)

    saved = client.patch(f"/api/ai/flashcard-sets/{fs['id']}/progress", json={"progress": {"0": "known", "1": "revise"}})
    assert saved.status_code == 200 and saved.json()["progress"] == {"0": "known", "1": "revise"}
    assert client.patch(f"/api/ai/flashcard-sets/{fs['id']}/progress", json={"progress": {"99": "known"}}).status_code == 422
    assert fs["id"] in [s["id"] for s in client.get("/api/ai/flashcard-sets").json()]
    client.delete(f"/api/documents/{doc['id']}")


def test_deleting_document_removes_its_quizzes_and_flashcards(client, upload, fake_ollama):
    doc = upload([PHOTOSYNTHESIS, ROMAN_EMPIRE])
    fs = client.post("/api/ai/generate-flashcards", json={"document_id": doc["id"], "num_cards": 3}).json()
    client.delete(f"/api/documents/{doc['id']}")
    assert fs["id"] not in [s["id"] for s in client.get("/api/ai/flashcard-sets").json()]


def test_dashboard(client, upload, fake_ollama):
    doc = upload([PHOTOSYNTHESIS])
    client.post("/api/chat", json={"question": "chlorophyll light photosynthesis", "document_ids": [doc["id"]]})
    body = client.get("/api/analytics/dashboard").json()
    assert body["total_documents"] >= 1 and body["total_questions"] >= 1
    assert len(body["activity"]) == 7
    assert body["recent_documents"]
    client.delete(f"/api/documents/{doc['id']}")
