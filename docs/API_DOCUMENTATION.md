# API Documentation

Base URL: `http://localhost:8000`. Interactive documentation (Swagger UI): `/docs`. All bodies are JSON except the upload (multipart). Errors always look like `{"detail": "message"}`.

| Status | Meaning |
|---|---|
| 200 / 202 / 204 | OK / accepted (processing in background) / deleted |
| 400 | invalid upload (not a PDF, corrupted, encrypted, empty) |
| 404 | document, chat, quiz or flashcard set not found |
| 409 | document exists but is not `ready` |
| 413 | file larger than the limit |
| 422 | request validation failed |
| 502 | model answered but output was unusable (e.g. malformed quiz JSON) |
| 503 | Ollama is unreachable, the model is missing, or it timed out |
| 500 | unexpected error (details only in the server log) |

## Health and system
- `GET /api/health` → `{"status":"ok","app":"StudyMate AI","version":"1.0.0"}`
- `GET /api/system/status` → backend, Ollama (`reachable`, `model`, `model_available`, `installed_models`), embeddings (`backend`, `model`, `loaded`), database, vector store, active configuration.

## Documents
- `POST /api/documents/upload` – multipart field `file`. Returns **202** with the document (`processing_status: "processing"`). Poll `GET /api/documents/{id}` until `ready` or `failed` (`error_message` explains why).
- `GET /api/documents?q=text` – list, newest first, optional filename filter.
- `GET /api/documents/{document_id}`
- `DELETE /api/documents/{document_id}` – removes SQLite rows, the PDF and ChromaDB vectors.

Document object: `id, original_filename, upload_date, processing_status, page_count, file_size, chunk_count, error_message`.

## Chat
`POST /api/chat`
```json
{ "question": "What is osmosis?", "chat_id": null, "document_ids": ["<id>"] }
```
- `document_ids` empty → search all ready documents.
- `chat_id` null → a new conversation is created.

Response:
```json
{
  "answer": "…",
  "chat_id": "…",
  "sources": [{"document_id":"…","filename":"bio.pdf","page_number":3,"excerpt":"…","score":0.71}],
  "info": {"retrieved_chunks":4,"model":"llama3.2:1b","grounded":true,"llm_called":true,"elapsed_ms":8123}
}
```
If nothing relevant is found: `grounded:false`, `llm_called:false`, no sources, and an honest "does not provide enough information" answer.

- `GET /api/chats` – conversations, newest first.
- `GET /api/chats/{chat_id}` – with all messages and their sources.
- `DELETE /api/chats/{chat_id}`

## AI tools
- `POST /api/ai/summarize` `{ "document_id", "mode": "short" | "detailed" }` → `summary, key_concepts[], definitions[{term,definition}], exam_notes[], sections_total, sections_used`.
- `POST /api/ai/generate-quiz` `{ "document_id", "difficulty": "easy|medium|hard", "num_questions": 1-20 }` → `quiz_id, questions[{question, options[4]}], warning`. **Correct answers are not included.**
- `POST /api/ai/submit-quiz` `{ "quiz_id", "answers": [0-3 | null, …] }` → `score, total, results[{question, options, selected, correct_index, correct, explanation}]`. Submitting an already-submitted quiz stores a new attempt.
- `GET /api/ai/quiz-history` – completed attempts.
- `POST /api/ai/generate-flashcards` `{ "document_id", "num_cards": 1-30 }` → set with `cards[{question, answer, key_concept, source_page}]`, `progress`.
- `GET /api/ai/flashcard-sets`
- `PATCH /api/ai/flashcard-sets/{id}/progress` `{ "progress": {"0":"known","3":"revise"} }`

## Analytics
`GET /api/analytics/dashboard` → totals (documents, questions, completed quizzes), `average_quiz_score` (percent), recent documents and chats, and 7-day `activity`.
