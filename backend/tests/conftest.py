"""Test setup: temporary data folder + offline test embedder. No Ollama and no model downloads."""
import os
import tempfile

# These must be set BEFORE the app is imported (settings are read once at import time).
_TMP = tempfile.mkdtemp(prefix="studymate_test_")
os.environ["DATA_DIR"] = _TMP
os.environ["EMBEDDING_BACKEND"] = "hash"
os.environ["RELEVANCE_THRESHOLD"] = "0.12"
os.environ["TOP_K"] = "4"

import json  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

try:
    import pymupdf as fitz  # noqa: E402
except ImportError:  # pragma: no cover
    import fitz  # type: ignore  # noqa: E402

from app.main import app  # noqa: E402
from app.services import ollama_service  # noqa: E402

PHOTOSYNTHESIS = (
    "Photosynthesis is the process plants use to convert sunlight into chemical energy. "
    "Chloroplasts contain chlorophyll which absorbs light. Plants take carbon dioxide and water "
    "and produce glucose and oxygen during photosynthesis in the leaves."
)
ROMAN_EMPIRE = (
    "The Roman Empire was ruled by emperors after Augustus founded the principate. "
    "Roman legions defended the borders and roads connected the provinces. "
    "The capital city Rome housed the senate and the forum."
)


def make_pdf(pages) -> bytes:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(50, 50, 550, 780), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def upload(client):
    def _upload(pages, name="notes.pdf"):
        response = client.post(
            "/api/documents/upload", files={"file": (name, make_pdf(pages), "application/pdf")}
        )
        assert response.status_code == 202, response.text
        return response.json()

    return _upload


@pytest.fixture()
def fake_ollama(monkeypatch):
    """Replace the real Ollama call. Returns the list of calls so tests can inspect them."""
    calls = []
    counter = {"n": 0}

    def fake_chat(messages, json_mode=False, **kwargs):
        calls.append({"messages": messages, "json_mode": json_mode})
        prompt = messages[-1]["content"]
        if not json_mode:
            return "Mock answer about the document (page 1)."
        counter["n"] += 1
        n = counter["n"]
        if "multiple-choice" in prompt:
            return json.dumps(
                {
                    "questions": [
                        {
                            "question": f"Question number {n}{i} about the passage?",
                            "options": [f"right {n}{i}", f"wrong A {n}{i}", f"wrong B {n}{i}", f"wrong C {n}{i}"],
                            "correct_index": 0,
                            "explanation": "Because the passage says so.",
                        }
                        for i in range(2)
                    ]
                }
            )
        if "flashcard" in prompt:
            return json.dumps(
                {
                    "flashcards": [
                        {"question": f"What is concept {n}{i}?", "answer": f"Answer {n}{i}", "key_concept": f"concept {n}{i}"}
                        for i in range(3)
                    ]
                }
            )
        return json.dumps(
            {
                "summary": "This is a mocked summary of the study material.",
                "key_concepts": ["photosynthesis", "chlorophyll"],
                "definitions": [{"term": "Chlorophyll", "definition": "A green pigment."}],
                "exam_notes": ["Remember the inputs and outputs."],
            }
        )

    monkeypatch.setattr(ollama_service, "chat", fake_chat)
    return calls
