"""Retrieval-Augmented Generation: retrieve relevant chunks, build a grounded prompt, ask Ollama.

This module has no FastAPI imports, so it can be tested and reused on its own.
"""
import time
from typing import Any, Dict, List, Optional, Sequence

from app.core.config import settings
from app.services import embedding_service, ollama_service, vector_store

SYSTEM_PROMPT = """You are StudyMate AI, an educational assistant answering questions from extracted document excerpts.

The text below has already been extracted from the student's uploaded document. You do not need to open or inspect a file. Answer the student's question directly using those excerpts.

Never refuse just because the source is a file or because you cannot access a file. The excerpt text is provided to you here.

Do not invent information. If the excerpts do not contain enough information to answer, say that the provided text does not contain the answer.

Explain concepts in simple educational language.

Use the source material accurately, and refer to its page number when useful.

Do not pretend that external knowledge came from the uploaded document."""

NOT_ENOUGH_INFO = (
    "The uploaded document does not provide enough information to answer this question. "
    "Try rephrasing it, or select a different document."
)
NO_DOCUMENTS = "There are no processed documents yet. Upload a PDF in My Documents first."


def retrieve(
    question: str,
    document_ids: Optional[Sequence[str]] = None,
    top_k: Optional[int] = None,
    threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Semantic search, optionally limited to some documents, dropping weak matches."""
    top_k = top_k or settings.top_k
    threshold = settings.relevance_threshold if threshold is None else threshold
    embedding = embedding_service.embed_query(question)
    hits = vector_store.query(embedding, document_ids, top_k)
    return [h for h in hits if h["score"] >= threshold]


def _format_context(chunks: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    used = 0
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk["metadata"]
        block = f"[Excerpt {i}, page {meta['page_number']}]\n{chunk['text']}"
        if used + len(block) > settings.max_context_chars and parts:
            break  # keep the prompt small enough for a 1B model on an 8 GB laptop
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)


def build_messages(
    question: str, chunks: List[Dict[str, Any]], history: Sequence[Dict[str, str]]
) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in list(history)[-settings.history_messages :]:  # never send unlimited history
        messages.append({"role": turn["role"], "content": turn["content"][:800]})
    messages.append(
        {
            "role": "user",
            "content": f"Document context:\n{_format_context(chunks)}\n\nStudent question: {question}",
        }
    )
    return messages


def _to_sources(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sources = []
    for chunk in chunks:
        meta = chunk["metadata"]
        excerpt = chunk["text"]
        sources.append(
            {
                "document_id": meta["document_id"],
                "filename": meta["filename"],
                "page_number": meta["page_number"],
                "excerpt": excerpt if len(excerpt) <= 320 else excerpt[:317] + "...",
                "score": chunk["score"],
            }
        )
    return sources


def answer_question(
    question: str,
    document_ids: Optional[Sequence[str]],
    history: Sequence[Dict[str, str]],
    has_any_documents: bool = True,
) -> Dict[str, Any]:
    started = time.perf_counter()

    # Very short follow-ups ("and why?") are searched together with the previous question.
    search_text = question
    if len(question.split()) <= 4:
        previous = [h["content"] for h in history if h["role"] == "user"]
        if previous:
            search_text = f"{previous[-1]} {question}"

    chunks = retrieve(search_text, document_ids)
    info: Dict[str, Any] = {"retrieved_chunks": len(chunks), "model": settings.chat_model}

    if not chunks:
        info.update(grounded=False, llm_called=False, elapsed_ms=int((time.perf_counter() - started) * 1000))
        return {
            "answer": NOT_ENOUGH_INFO if has_any_documents else NO_DOCUMENTS,
            "sources": [],
            "info": info,
        }

    answer = ollama_service.chat(build_messages(question, chunks, history), temperature=0.2)
    info.update(grounded=True, llm_called=True, elapsed_ms=int((time.perf_counter() - started) * 1000))
    return {"answer": answer, "sources": _to_sources(chunks), "info": info}
