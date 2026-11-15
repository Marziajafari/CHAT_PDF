"""MANUAL integration test against the REAL local model (Ollama + sentence-transformers).

Prerequisites: `ollama serve` running, `ollama pull llama3.2:1b` done, backend running on :8000.
Usage (from backend/):  python scripts/manual_integration_test.py path/to/some.pdf
"""
import sys
import time

import httpx

BASE = "http://localhost:8000/api"


def main(pdf_path: str) -> None:
    with httpx.Client(timeout=600) as client:
        status = client.get(f"{BASE}/system/status").json()
        print("Ollama:", status["ollama"])
        if not status["ollama"]["reachable"] or not status["ollama"]["model_available"]:
            sys.exit("Ollama or the model is not available - fix that first.")

        with open(pdf_path, "rb") as f:
            doc = client.post(f"{BASE}/documents/upload", files={"file": (pdf_path.split("/")[-1], f, "application/pdf")}).json()
        print("Uploaded:", doc["id"], doc["processing_status"])
        for _ in range(120):
            doc = client.get(f"{BASE}/documents/{doc['id']}").json()
            if doc["processing_status"] != "processing":
                break
            time.sleep(2)
        print("Processing result:", doc["processing_status"], doc.get("error_message"))
        assert doc["processing_status"] == "ready"

        answer = client.post(f"{BASE}/chat", json={"question": "What is this document about?", "document_ids": [doc["id"]]}).json()
        print("\nANSWER:", answer["answer"])
        print("SOURCES:", [(s["filename"], s["page_number"]) for s in answer["sources"]])

        unanswerable = client.post(f"{BASE}/chat", json={"question": "What is the airspeed velocity of an unladen swallow on Mars?", "document_ids": [doc["id"]]}).json()
        print("\nUNANSWERABLE ->", unanswerable["answer"])

        summary = client.post(f"{BASE}/ai/summarize", json={"document_id": doc["id"], "mode": "short"}).json()
        print("\nSUMMARY:", summary["summary"][:300])

        quiz = client.post(f"{BASE}/ai/generate-quiz", json={"document_id": doc["id"], "difficulty": "easy", "num_questions": 3}).json()
        print("\nQUIZ questions:", len(quiz["questions"]), quiz.get("warning"))

        cards = client.post(f"{BASE}/ai/generate-flashcards", json={"document_id": doc["id"], "num_cards": 3}).json()
        print("FLASHCARDS:", len(cards["cards"]))

        client.delete(f"{BASE}/documents/{doc['id']}")
        print("\nDone. Document deleted (SQLite + vectors).")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
