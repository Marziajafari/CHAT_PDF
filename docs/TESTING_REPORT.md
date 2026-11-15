# Testing Report

> **Status: automated tests were written but NOT executed by the author of this code.**
> The environment where the project was generated had no internet, so Python packages, npm packages and Ollama could not be installed. Only the pure-Python text logic (chunking, JSON extraction, selection helper) and the hash-embedder similarity values used by the tests were run and checked, plus a Python syntax check of every backend file. **Everything else must be run on your laptop, and the real results pasted into section 4 below.** Do not claim passing results in your report until you have seen them yourself.

## 1. Test strategy
| Level | Tool | Needs Ollama? | Needs model download? |
|---|---|---|---|
| Backend unit + API | Pytest + FastAPI TestClient | No (Ollama is mocked) | No (test embedder `hash`) |
| Frontend components | Vitest + React Testing Library | No (API module mocked) | No |
| Manual integration | `backend/scripts/manual_integration_test.py` | **Yes** | Yes (MiniLM) |

The automated backend tests use a temporary data folder, so your real documents are never touched. Ollama is replaced only for chat/summary/quiz/flashcard generation. PDF extraction, chunking, ChromaDB storage, retrieval, filtering, SQLite and all endpoints run for real.

## 2. Backend test inventory (`backend/tests/`)
| Requirement | Test |
|---|---|
| Application startup, health, Swagger | `test_health.py` |
| Invalid PDF rejection (extension, fake content, corrupted, empty) | `test_documents.py` |
| Path traversal filename neutralised | `test_path_traversal_filename_is_neutralised` |
| Valid upload + processing | `test_valid_upload_processes_and_is_listed` |
| PDF text extraction (page-aware) | `test_extraction_is_page_aware` |
| Image-only PDF handled | `test_pdf_without_text_is_marked_failed` |
| Chunk generation | `test_text_utils.py` |
| Embedding generation | `test_embedding_generation` |
| Vector storage and retrieval | `test_vector_storage_and_retrieval` |
| Document filtering | `test_retrieval_filters_by_document` |
| Irrelevant question → no context | `test_irrelevant_question_returns_nothing` |
| Chat endpoint, sources, history, deletion | `test_chat.py` |
| Unanswerable question handled honestly, model not called | `test_unanswerable_question_...` |
| Ollama down → clear 503 | `test_ollama_down_gives_clear_503` |
| Summary endpoint (incl. long documents) | `test_summarize*` |
| Quiz generation, hidden answers, scoring, retake | `test_quiz_generation_hides_answers_and_scores` |
| Malformed AI output rejected | `test_malformed_model_output_is_rejected`, `test_non_json_...` |
| Flashcards + progress | `test_flashcards_and_progress` |
| Database persistence | `test_data_persists_in_a_new_database_session` |
| Document deletion (row, file, vectors, cascades) | `test_delete_removes_...`, `test_deleting_document_removes_...` |
| Dashboard analytics | `test_dashboard` |

Run: `cd backend && pytest -v`

## 3. Frontend test inventory (`frontend/src/__tests__/`)
Dashboard rendering and error state, sidebar navigation through six pages, document upload (success, backend error, search, empty state), chat (empty state, user message, loading indicator, answer with page sources, error, selected documents sent), full quiz flow (generate, answer, disabled submit, results, explanations, retry), quiz error state.

Run: `cd frontend && npm test`

## 4. Actual results (fill in after running)
| Date | Command | Result (copy the summary line) | Notes / fixes made |
|---|---|---|---|
| | `pytest -v` | | |
| | `npm test` | | |
| | `npm run build` (type check) | | |

If something fails, copy the first error into a note here, fix it, and record the re-run. Honest "found 3 bugs, fixed them" notes are good material for the report.

## 5. Manual integration test (real model)
1. Start Ollama, the backend and make sure `ollama pull llama3.2:1b` is done.
2. `python backend/scripts/manual_integration_test.py path/to/lecture.pdf`
3. Record: upload/processing time, answer quality, whether the "unanswerable" question was refused, summary, quiz and flashcard counts, time per step.

| Step | Time on your laptop | Observation |
|---|---|---|
| Upload + processing | | |
| Question (grounded) | | |
| Question (unanswerable) | | |
| Short summary | | |
| Quiz (3 questions) | | |
| Flashcards (3 cards) | | |

## 6. Manual UI checklist
- [ ] Dashboard loads; numbers change after actions
- [ ] Drag-and-drop upload; progress bar; status turns Ready
- [ ] Wrong file (txt renamed to pdf) shows a clear error
- [ ] Delete a document; it disappears; chat with it no longer finds it
- [ ] Chat shows sources with page numbers; "Clear conversation" works
- [ ] History page opens an old chat and can delete it
- [ ] Summary short/detailed, copy button
- [ ] Quiz: cannot submit with unanswered questions; results show explanations; Retry works
- [ ] Flashcards flip, next/previous, known/revise persist after reload (open "Saved sets")
- [ ] Settings shows Ollama status; stop Ollama and press refresh → Problem
- [ ] Restart backend: all data still there
