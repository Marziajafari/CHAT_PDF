# Architecture

## 1. System overview
```mermaid
flowchart TB
  subgraph Browser
    UI[React + TypeScript UI]
  end
  subgraph Backend[FastAPI backend]
    R[API routes: thin HTTP layer]
    S1[document_service + pdf_service]
    S2[rag_service]
    S3[ai_tasks: summary, quiz, flashcards]
    S4[embedding_service]
    S5[vector_store]
    S6[ollama_service]
  end
  UI -- REST JSON --> R
  R --> S1 & S2 & S3
  S1 --> S4
  S1 --> S5
  S2 --> S4
  S2 --> S5
  S2 --> S6
  S3 --> S5
  S3 --> S6
  S5 --> CH[(ChromaDB on disk)]
  R --> DB[(SQLite via SQLAlchemy)]
  S6 --> OL[Ollama: Llama 3.2 1B]
```
Routes only translate HTTP to function calls and back. All logic lives in `app/services`, which does not import FastAPI, so it can be tested alone.
Long-document summaries group up to three sections per model request, and quiz requests generate up to three questions at a time to reduce serial model round trips.

## 2. Folder map
```
backend/app/
  api/        routes (system, documents, chat, ai, analytics) + deps
  core/       settings (config.py)
  db/         engine/session (database.py), tables (models.py)
  schemas/    Pydantic request/response + LLM output validators
  services/   pdf, text_utils, embedding, vector_store, ollama, rag, ai_tasks, document
frontend/src/
  pages/      one file per sidebar item
  components/ Layout (sidebar), DocumentPicker, ui primitives
  lib/        api.ts (all HTTP calls + types), utils.ts
```

## 3. Document ingestion
```mermaid
sequenceDiagram
  participant U as Student
  participant API as POST /documents/upload
  participant BG as Background task
  participant PDF as PyMuPDF
  participant EMB as MiniLM embedder
  participant CH as ChromaDB
  U->>API: PDF file
  API->>API: extension, size, %PDF header, open check, password check
  API->>API: save as <uuid>.pdf, insert row (status=processing)
  API-->>U: 202 Accepted
  API->>BG: process_document(id)
  BG->>PDF: extract text page by page
  BG->>BG: clean + chunk (700 chars, 100 overlap), keep page numbers
  loop batches of 32
    BG->>EMB: embed chunk texts
    BG->>CH: upsert vectors + metadata
  end
  BG->>BG: status = ready (or failed + reason)
  U->>API: polls GET /documents (every 2 s while processing)
```

## 4. RAG question answering
```mermaid
sequenceDiagram
  participant U as Student
  participant API as POST /chat
  participant RAG as rag_service
  participant CH as ChromaDB
  participant OL as Ollama
  U->>API: question + selected document ids
  API->>RAG: answer_question(question, ids, history)
  RAG->>RAG: embed question
  RAG->>CH: top-k cosine search, filter document_id in ids
  RAG->>RAG: drop chunks below relevance threshold
  alt nothing relevant
    RAG-->>API: "document does not provide enough information" (model NOT called)
  else relevant chunks
    RAG->>RAG: build prompt: system rules + last 6 messages + context + question
    RAG->>OL: chat request (num_ctx 4096)
    OL-->>RAG: answer
    RAG-->>API: answer + sources (file, page, excerpt, score)
  end
  API->>API: save user + assistant messages (SQLite)
  API-->>U: answer, chat_id, sources, info
```

## 5. Database (SQLite)
```mermaid
erDiagram
  DOCUMENTS ||--o{ QUIZ_HISTORY : has
  DOCUMENTS ||--o{ FLASHCARD_SETS : has
  DOCUMENTS ||--o{ CHATS : "optional link (SET NULL)"
  CHATS ||--o{ MESSAGES : contains
  DOCUMENTS {
    string id PK
    string filename
    string original_filename
    string file_path
    datetime upload_date
    string processing_status
    int page_count
    int file_size
    int chunk_count
    string error_message
  }
  CHATS {
    string id PK
    string title
    string document_id FK
    text document_ids_json
    datetime created_at
    datetime updated_at
  }
  MESSAGES {
    int id PK
    string chat_id FK
    string role
    text content
    text sources_json
    datetime created_at
  }
  QUIZ_HISTORY {
    string id PK
    string document_id FK
    string difficulty
    int score
    int total_questions
    text questions_json
    text answers_json
    datetime created_at
    datetime completed_at
  }
  FLASHCARD_SETS {
    string id PK
    string document_id FK
    string title
    text cards_json
    text progress_json
    datetime created_at
  }
```
Vectors live in ChromaDB (not SQLite). Each vector's metadata: `document_id`, `filename`, `page_number`, `chunk_index`. Deleting a document removes the SQLite row (cascading to quizzes and flashcards), the PDF file and all its vectors.

## 6. Quiz flow (answers stay on the server)
```mermaid
sequenceDiagram
  participant UI
  participant API
  participant LLM as Ollama
  UI->>API: generate-quiz(doc, difficulty, n)
  loop until n valid questions
    API->>LLM: passage -> 2 questions as JSON
    API->>API: validate with Pydantic (4 unique options, index 0-3, explanation)
  end
  API->>API: shuffle options, store questions + correct answers
  API-->>UI: questions and options only
  UI->>API: submit-quiz(quiz_id, answers)
  API-->>UI: score + correct answers + explanations
```

## 7. Use cases
```mermaid
flowchart LR
  S((Student))
  S --> A[Upload and manage PDFs]
  S --> B[Ask questions with sources]
  S --> C[Generate summaries]
  S --> D[Take quizzes]
  S --> E[Study flashcards]
  S --> F[Review chat history]
  S --> G[Check system status]
```

## 8. Design decisions
- **Page-aware chunks**: chunking is done per page so every passage can cite its page.
- **Relevance threshold**: weak matches are discarded; with no matches the model is not called, which prevents invented answers.
- **Small context**: at most `TOP_K` passages, 3000 characters of context and 6 history messages go to the 1B model.
- **Background processing**: upload returns immediately; the UI polls the status.
- **Lazy model loading**: the embedding model loads on first use, Ollama unloads the chat model after `OLLAMA_KEEP_ALIVE`.
- **JSON mode + validation**: small models produce imperfect JSON, so every question/card is validated individually and bad ones are dropped.
