# Viva Preparation: Questions and Answers

Answers are written in simple language but are technically correct. **Do not memorise them word for word:** read the matching code, then explain in your own words. Items 1-8 are theory, 9-25 are RAG and AI, then backend, frontend, quality and contribution.

**1. What is artificial intelligence?**  
Making computers do tasks that normally need human intelligence, such as understanding language, recognising images or making decisions. StudyMate AI uses AI to understand questions and write answers.

**2. What is machine learning?**  
A part of AI where a program learns patterns from data instead of being given fixed rules. Our embedding model and language model were both trained this way.

**3. What is deep learning?**  
Machine learning with many-layered neural networks. Both MiniLM and Llama are deep neural networks (Transformers).

**4. What is a large language model (LLM)?**  
A neural network trained on huge amounts of text to predict the next word (token). By repeating that prediction it can write answers, summaries and quiz questions. Llama 3.2 1B is a small LLM with about 1 billion parameters.

**5. What is a Transformer?**  
The neural network architecture (Vaswani et al., 2017, 'Attention Is All You Need') that uses attention to relate every word to every other word. Almost all modern LLMs and embedding models use it.

**6. What is Ollama?**  
A program that downloads and runs LLMs locally and offers a simple HTTP API on port 11434. My backend sends chat requests to it, so no cloud service is needed.

**7. Why Llama 3.2 1B?**  
It is small enough (roughly 1-2 GB in memory) to run on CPU with 8 GB RAM. The trade-off is lower answer quality than big models, which is why I ground it with retrieved context.

**8. What are tokens and the context window?**  
Tokens are word pieces the model reads. The context window is the maximum tokens the model can see at once. I set num_ctx to 4096 and limit prompt size so it never overflows.

**9. What does temperature do?**  
It controls randomness. I use low values (0.2) for answers and summaries for accuracy and 0.4 for quizzes to get some variety.

**10. What is RAG?**  
Retrieval-Augmented Generation: first retrieve relevant text from my documents, then give it to the model with the question so the answer is based on that text (Lewis et al., 2020).

**11. Why use RAG instead of just asking the model?**  
The model does not know my lecture notes, can invent facts, and cannot cite pages. RAG supplies the real text and lets me show sources.

**12. Why not fine-tune the model on the PDFs?**  
Fine-tuning needs a lot of compute and time, must be repeated for each new document and does not give page citations. RAG works instantly on new files.

**13. Explain your RAG pipeline step by step.**  
Upload, extract text per page, chunk, embed, store in ChromaDB. At question time: embed question, similarity search (filtered by document), drop weak matches, build prompt with system rules, history and context, call Ollama, return answer plus sources.

**14. What is an embedding?**  
A list of numbers (384 for MiniLM) representing the meaning of a text. Texts with similar meaning get vectors that point in similar directions.

**15. Why all-MiniLM-L6-v2?**  
It is small (about 90 MB), fast on CPU, good for semantic search and works offline after one download.

**16. What is semantic search?**  
Searching by meaning rather than exact words. 'Plants make food from light' can match 'photosynthesis' because their embeddings are close.

**17. What is cosine similarity?**  
A measure of the angle between two vectors, from -1 to 1. Chroma returns cosine distance; I convert it with score = 1 - distance. Higher means more similar.

**18. What is a vector database and why ChromaDB?**  
A database built to store vectors and quickly find the nearest ones. ChromaDB is lightweight, runs inside Python, stores data on disk and supports metadata filters.

**19. What is stored in ChromaDB?**  
For each chunk: the text, its embedding and metadata (document_id, filename, page_number, chunk_index).

**20. How does document filtering work?**  
The query uses a metadata filter on document_id (equals for one document, $in for several), so chunks from other documents are never retrieved.

**21. What is text chunking and why is it needed?**  
Splitting text into small passages. Embedding whole books loses detail and a small model cannot read them. Chunks give precise retrieval and fit the context window.

**22. Why 700 characters with 100 overlap?**  
700 characters is about one paragraph: big enough for meaning, small enough to be specific. Overlap keeps a sentence that falls on a boundary available in both chunks. Both values are configurable in .env.

**23. What is the relevance threshold?**  
A minimum similarity (0.25 default). Chunks below it are discarded, so unrelated text never reaches the model. If nothing remains, the system answers that the document lacks information.

**24. How do you prevent hallucination?**  
Grounding system prompt, only retrieved context, low temperature, refusal path without calling the model, and showing sources so the student can verify. It reduces but cannot fully eliminate errors.

**25. What is prompt engineering?**  
Designing the instructions given to the model. Mine has a system prompt with rules (do not invent, say when information is missing, cite pages) and a user message with context plus question.

**26. How do you handle conversation history?**  
Messages are stored in SQLite. Only the last 6 messages, each cut to 800 characters, are sent to Ollama, so the prompt stays small.

**27. How do you handle follow-up questions like 'and why?'**  
Very short questions are searched together with the previous user question so retrieval still has meaning.

**28. How is PDF text extracted?**  
With PyMuPDF page by page, so every chunk keeps its page number. I clean whitespace and re-join hyphenated words.

**29. What if the PDF is scanned, encrypted or corrupted?**  
Corrupted or encrypted PDFs are rejected at upload with a clear 400 message. Scanned PDFs have no text, so the document is marked failed with an explanation. OCR is a future improvement.

**30. How do you validate uploads?**  
Extension, size limit (20 MB), %PDF header check, a real open with PyMuPDF, password check, and a random UUID file name so user-supplied names cannot cause path traversal.

**31. Why process documents in a background task?**  
Embedding takes time. The upload returns 202 immediately, the UI shows 'Processing' and polls until Ready.

**32. What is FastAPI and why use it?**  
A modern Python web framework with automatic validation (Pydantic), async support and built-in Swagger docs at /docs.

**33. What is Pydantic used for?**  
Validating request bodies and responses, and validating the JSON produced by the language model (for example exactly four unique options).

**34. What is a REST API?**  
A style where resources have URLs and HTTP methods (GET, POST, PATCH, DELETE) express actions, with JSON bodies and status codes.

**35. Explain the status codes you use.**  
202 accepted, 400 bad upload, 404 not found, 409 document not ready, 413 too large, 422 validation, 502 bad AI output, 503 Ollama unavailable.

**36. Why keep routes separate from services?**  
Routes handle HTTP only; services contain logic and do not import FastAPI. That makes the RAG code testable and replaceable.

**37. What is CORS?**  
A browser rule restricting which websites may call an API. I allow only the local frontend origin; in development the Vite proxy avoids the issue entirely.

**38. Why SQLite and SQLAlchemy?**  
SQLite is a zero-setup file database, perfect for a local single-user app. SQLAlchemy maps Python classes to tables so I write less raw SQL and get relationships and foreign keys.

**39. Describe your database schema.**  
documents, chats, messages, quiz_history, flashcard_sets, with foreign keys: messages to chats (cascade), quizzes and flashcards to documents (cascade), chats to documents (SET NULL).

**40. Why store vectors in ChromaDB and not SQLite?**  
Nearest-neighbour search over vectors needs a special index (HNSW). SQLite stores the relational data.

**41. What happens when a document is deleted?**  
Vectors are deleted from ChromaDB, the PDF file is removed, and the SQLite row is deleted with its quizzes and flashcards cascading. Tests verify this.

**42. What is React and why TypeScript?**  
React builds UIs from components that re-render when state changes. TypeScript adds types, catching mistakes such as a wrong field name before running.

**43. What is TanStack Query used for?**  
Fetching and caching server data, loading and error states, and automatic refetching (for example polling while a document is processing).

**44. How does the frontend talk to the backend?**  
Axios calls /api/...; the Vite dev server proxies to FastAPI on port 8000. All calls and types are in lib/api.ts.

**45. How does the quiz generation work?**  
The document is split into passages; for each, the model is asked for two questions as JSON. Each question is validated with Pydantic, invalid or duplicate ones are dropped, options are shuffled, and the quiz is stored.

**46. How do you keep quiz answers secret?**  
The generate endpoint returns only questions and options. Correct answers and explanations stay in the database until submit-quiz, which scores on the server.

**47. What if the model returns invalid JSON?**  
I use Ollama JSON mode, parse tolerantly, validate each item, skip bad ones, retry other passages, and return 502 with a clear message if nothing valid is produced.

**48. How does summarisation work for a long PDF?**  
Map-reduce: split into ~3000-character sections (maximum 8, chosen evenly), summarise each, combine, then produce a final structured JSON summary. This keeps every call inside the context limit.

**49. How are flashcards generated and tracked?**  
Similar to the quiz: JSON cards with question, answer and key concept plus the source page. Known/revise status is saved with PATCH and restored when the set is reopened.

**50. How did you optimise for 8 GB RAM?**  
1B model, CPU inference, small embedding model loaded lazily, batch embedding (32), top-k 4, 3000 character context, 6 message history, Ollama keep-alive 5 minutes, no extra services.

**51. What are the limitations of your system?**  
Small model quality, no OCR, English-centred embeddings, slow on CPU, retrieval can miss information spread across many pages, single user without login.

**52. How could the project be improved?**  
OCR for scans, multilingual embeddings (useful for Kazakh and Russian), hybrid keyword plus vector search, re-ranking, streaming answers, authentication, larger models if hardware allows.

**53. How is data privacy handled?**  
All processing is local: Ollama, embeddings, ChromaDB and SQLite run on the laptop. No document text is sent to any cloud service, and data/ is excluded from Git.

**54. How did you test the system?**  
Pytest with FastAPI TestClient (Ollama mocked, test embedder) for backend, Vitest with Testing Library for the UI, plus a manual integration script with the real model. Results are in TESTING_REPORT.md.

**55. Why mock Ollama in tests?**  
Tests must be fast, repeatable and run without a 1 GB model. Everything else (PDF, ChromaDB, SQLite, endpoints) runs for real, and the real model is tested manually.

**56. What is the difference between unit and integration tests?**  
Unit tests check one function (e.g. chunking); integration tests check components together (upload, then retrieve, then chat).

**57. What was your individual contribution?**  
Be specific and honest: the architecture, ingestion pipeline, RAG service, validation of AI output, UI pages and tests. Name the libraries you used but did not write. (See DEMO_SCRIPT.md.)

**58. Which part was hardest and what did you learn?**  
Prepare your own answer: for example making a 1B model return reliable JSON, or balancing retrieval threshold between missing answers and irrelevant context.

**59. What would you change if you had a GPU or 16 GB RAM?**  
Use a bigger model (e.g. 3B-8B) for better answers, raise top-k, use a stronger embedding model, and generate quizzes in fewer calls.


*Total: 59 questions.* Also see the follow-up questions list in DEMO_SCRIPT.md.