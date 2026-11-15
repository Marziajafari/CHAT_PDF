# Installation Guide

Tested target: a laptop with **8 GB RAM, no dedicated GPU**. (Instructions are written for Windows; macOS/Linux differences are noted.)

## 1. Install the prerequisites
| Tool | Version | Check |
|---|---|---|
| Python | 3.11 or 3.12 (3.13 can break ChromaDB / PyTorch wheels) | `python --version` |
| Node.js | 20 or newer | `node --version` |
| Git | any | `git --version` |
| Ollama | latest, from https://ollama.com | `ollama --version` |

Free disk space: about 5 GB (PyTorch, models, node_modules).

## 2. Download the local chat model (once)
```bash
ollama pull llama3.2:1b
```
Ollama runs as a background service. If `ollama list` fails, start it with `ollama serve`.

## 3. Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
python scripts/download_embedding_model.py     # once; needs internet (~90 MB)
uvicorn app.main:app --port 8000
```
Check: http://localhost:8000/api/health returns `{"status":"ok"...}` and http://localhost:8000/docs shows Swagger UI.

After the embedding model is downloaded once, the app loads it from the local cache and does not download it again.

## 4. Frontend (second terminal)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. The Vite dev server forwards `/api` to port 8000, so no CORS setup is needed during development.

Production-style build: `npm run build` then `npm run preview` (also proxies `/api`).

## 5. Run the tests
```bash
cd backend && pytest
cd frontend && npm test
```

## 6. Start again after a restart
1. Make sure Ollama is running.
2. `cd backend`, activate the venv, `uvicorn app.main:app --port 8000`.
3. `cd frontend`, `npm run dev`.

Your documents, chats, quizzes and vectors are stored in `backend/data/` and survive restarts.

## Configuration (`backend/.env`)
See `.env.example`. The most useful settings: `CHAT_MODEL` (any model you pulled with Ollama), `TOP_K`, `RELEVANCE_THRESHOLD`, `CHUNK_SIZE`, `CHUNK_OVERLAP`.
Changing `EMBEDDING_MODEL` requires re-uploading documents because vectors from different models are not compatible.

## Troubleshooting
**Settings page shows Ollama "Not reachable"** – run `ollama serve`, then press "Refresh status".

**"Model 'llama3.2:1b' is not installed"** – run `ollama pull llama3.2:1b`.

**Computer becomes slow or answers time out (low memory)**
1. Close browser tabs and other heavy programs; a 1B model needs roughly 1.5–2.5 GB, the embedding model ~0.5 GB, the browser the rest.
2. Lower `OLLAMA_NUM_CTX` to `2048` and `TOP_K` to `3` in `.env`.
3. Lower `OLLAMA_NUM_PREDICT` to `300` for shorter answers.
4. Set `OLLAMA_KEEP_ALIVE=1m` so Ollama frees the model sooner.
5. Generate fewer quiz questions / flashcards at once (5 instead of 15).
6. Keep PDFs under ~100 pages for the first tests.

**Upload says "No extractable text"** – the PDF is a scan (images). Run OCR on it first; OCR is not part of this project.

**`pip install` fails on chromadb / torch** – check `python --version` is 3.11 or 3.12, upgrade pip (`python -m pip install -U pip`), and retry. If PyTorch is huge or fails, install the CPU build: `pip install torch --index-url https://download.pytorch.org/whl/cpu` and then the remaining requirements.

**Port already in use** – start uvicorn with `--port 8001` and change the proxy target in `frontend/vite.config.ts`.
