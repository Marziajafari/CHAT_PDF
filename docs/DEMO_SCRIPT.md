# Demonstration Scripts

## Before you start (do this 10 minutes earlier)
1. Close other programs. Start Ollama. Start backend and frontend.
2. Open Settings: Ollama must show OK. Run one chat question once so the model is loaded in RAM (the first answer is slowest).
3. Prepare a **short, text-based PDF** (10-20 pages). Pre-upload one document, and keep a second PDF ready for the live upload.
4. Prepare 1 answerable question, 1 unanswerable question, one summary and a 3-question quiz. Slow steps: practise them so you know the waiting time.

## 5-minute script
| Time | Action | What to say |
|---|---|---|
| 0:00 | Dashboard | "StudyMate AI is a local study assistant. The AI model, vector database and my documents all stay on my laptop." |
| 0:30 | My Documents: drop the second PDF | "On upload the backend validates the PDF, extracts text page by page, splits it into overlapping chunks, embeds them with MiniLM and stores them in ChromaDB." |
| 1:15 | AI Chat: ask the answerable question | "The question is embedded, ChromaDB finds the most similar chunks, and only those chunks are given to Llama 3.2 1B." |
| 2:00 | Open Sources | "Every answer shows document and page number, plus the passage it used." |
| 2:20 | Ask the unanswerable question | "If nothing relevant is found, the system says so and does not even call the model. That is how I avoid made-up answers." |
| 3:00 | Quiz: generate 3 easy questions, answer, submit | "The model writes JSON; I validate every question; the correct answers stay on the server until I submit." |
| 4:15 | Flashcards: flip, mark known | "Progress is saved in SQLite." |
| 4:45 | Settings | "Here I can see Ollama, the embedding model, database and vector store status." |

## 10-minute script
Follow the 5-minute script, but add:
- **(after Documents)** Show search and delete. Explain: "Deleting removes the SQLite row, the PDF file and all vectors."
- **(after Chat)** Select two documents and ask a question that only one contains: "Filtering by document id prevents contamination." Open Chat History and reload an old conversation.
- **Summaries** (2 min): Generate short summary, then detailed. Explain map-reduce: "Long PDFs are summarised section by section and then combined, so the model's context limit is never exceeded."
- **Code walkthrough** (2 min): show `rag_service.py` (retrieve → build_messages → answer_question) and the system prompt. Show `api/chat.py` is thin.
- **Tests** (1 min): run `pytest` and show the result you actually obtained. Mention that Ollama is mocked in automated tests and the real model is covered by the manual integration script.
- **Limitations** (30 s): 1B model quality, no OCR, English-centred embedding model, single user.

## If something goes wrong during the demo
- *Answer is slow*: "A 1B model on CPU needs time; that is the trade-off for being fully local."
- *Ollama error banner*: Open Settings, start `ollama serve`, refresh.
- *Quiz returns fewer questions*: the warning explains it; "invalid model output is rejected rather than shown".

## Likely examiner follow-up questions
1. Why not use the ChatGPT API? (privacy, cost, assignment requirement, offline)
2. How do you know the answer comes from the document and not from the model's memory?
3. What happens if the PDF is a scan? Password-protected? 500 pages?
4. Why chunk size 700 and overlap 100? What happens if they change?
5. What is cosine similarity? What is your relevance threshold and why?
6. Why Llama 3.2 1B? What would you change with 16 GB RAM?
7. How do you stop the quiz answers leaking to the browser?
8. What if the model returns invalid JSON?
9. How is the data stored, and what happens on delete?
10. What did you implement yourself and what is a library?

## What I personally implemented (edit to match the truth, then learn it)
- The whole backend design: layered routes/services structure, SQLite schema, validation rules.
- The ingestion pipeline: page-aware cleaning and chunking, batching, ChromaDB metadata and deletion.
- The RAG service: retrieval with document filter and threshold, grounding prompt, bounded history and context, the honest "not enough information" path.
- Quiz/flashcard/summary generation: prompts, JSON validation with Pydantic, deduplication, option shuffling, server-side scoring, map-reduce summaries.
- The React interface: eight pages, API client, loading/error/empty states, tests.
- **Libraries I used, not wrote**: FastAPI, SQLAlchemy, PyMuPDF, ChromaDB, Sentence Transformers, Ollama and the Llama model, React and Tailwind.

> Be careful: only say "I implemented" what you really understand. Read the code until you can explain each file. This project was generated with AI assistance, so check whether your university requires you to declare that.
