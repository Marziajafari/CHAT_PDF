"""Summaries, quizzes and flashcards. Every task is grounded in the uploaded document's own text."""
import logging
import math
import random
from typing import Any, Dict, List, Sequence, Tuple

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.schemas import GeneratedCard, GeneratedQuestion
from app.services import ollama_service
from app.services.errors import AiGenerationError
from app.services.text_utils import (
    chunk_text,
    extract_json,
    normalize_card,
    normalize_question,
    pick_evenly,
)

log = logging.getLogger("studymate.ai")

SECTION_CHARS = 3000   # size of one piece fed to the model during summarisation
MAX_SECTIONS = 8       # cap so very large PDFs still finish in reasonable time
PARTIAL_CHARS = 700    # each section summary is clipped to this length before combining


# ------------------------------------------------------------------ summaries
def _json_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _coerce_lists(data: Any) -> Dict[str, Any]:
    """Read key concepts, definitions and exam notes from the model's JSON (tolerant)."""
    if not isinstance(data, dict):
        raise ValueError("not an object")

    def as_text(item: Any) -> str:
        if isinstance(item, dict):
            return " - ".join(str(v) for v in item.values())
        return str(item)

    definitions = []
    for item in _json_list(data.get("definitions")):
        if isinstance(item, dict) and item.get("term") and item.get("definition"):
            definitions.append({"term": str(item["term"]), "definition": str(item["definition"])})
    return {
        "key_concepts": [as_text(i) for i in _json_list(data.get("key_concepts"))],
        "definitions": definitions,
        "exam_notes": [as_text(i) for i in _json_list(data.get("exam_notes"))],
    }


def _plain(messages: List[Dict[str, str]], num_predict: int) -> str:
    return ollama_service.chat(messages, temperature=0.3, num_predict=num_predict).strip()


def summarize(pages: Sequence[Tuple[int, str]], mode: str) -> Dict[str, Any]:
    """Map-reduce summary. The summary is written as plain text (small models write much
    better prose outside JSON); the lists are requested separately as JSON."""
    full_text = "\n\n".join(text for _, text in pages)
    if not full_text.strip():
        raise AiGenerationError("The document has no text to summarise.")

    sections = chunk_text(full_text, SECTION_CHARS, 0)
    used = pick_evenly(sections, MAX_SECTIONS)

    # keep the input small enough that Ollama does not silently cut it off
    budget = max(1500, min(6000, int((settings.ollama_num_ctx - 900) * 3.5)))

    if len(used) == 1:
        source = used[0]
    else:
        partials = []
        for number, section in enumerate(used, start=1):
            partials.append(
                _plain(
                    [
                        {
                            "role": "system",
                            "content": "You summarise study material accurately. Use only the given text.",
                        },
                        {
                            "role": "user",
                            "content": f"Part {number} of the document:\n{section}\n\n"
                            "Summarise this part in 4 to 6 complete sentences, covering all of its main points.",
                        },
                    ],
                    num_predict=250,
                )[:PARTIAL_CHARS]
            )
        source = "\n\n".join(f"Part {i}: {p}" for i, p in enumerate(partials, start=1))
    source = source[:budget]

    if mode == "short":
        task = (
            "Write a clear summary of the material below as one paragraph of 5 to 7 complete sentences. "
            "Cover the main idea, the key points and the conclusion. Do not answer in one line."
        )
        min_chars, num_predict = 300, 400
    else:
        task = (
            "Write a detailed summary of the material below in 3 to 5 paragraphs. Each paragraph covers a "
            "different part or idea, with the important details, names, steps and conclusions. "
            "Be as thorough as the material allows."
        )
        min_chars, num_predict = 700, 900

    messages = [
        {
            "role": "system",
            "content": "You are StudyMate AI, a careful study assistant. Use only the supplied material and never add facts that are not in it.",
        },
        {"role": "user", "content": f"{task}\n\nMaterial:\n{source}"},
    ]
    summary = _plain(messages, num_predict)
    if len(summary) < min_chars and len(source) > 600:
        retry = messages + [
            {"role": "assistant", "content": summary},
            {
                "role": "user",
                "content": "That is too short. Rewrite the summary with much more detail, in full sentences, "
                "using only the material.",
            },
        ]
        longer = _plain(retry, num_predict)
        if len(longer) > len(summary):
            summary = longer
    if not summary:
        raise AiGenerationError("The model returned an empty summary. Please try again.")

    if mode == "short":
        sizes = "key_concepts: 3 to 5 short items; definitions: up to 3; exam_notes: 3 to 4 short sentences."
    else:
        sizes = "key_concepts: 6 to 10 short items; definitions: up to 6; exam_notes: 5 to 8 short sentences."
    lists_prompt = (
        'From the material below produce JSON with exactly these keys: "key_concepts" (list of strings), '
        '"definitions" (list of objects with "term" and "definition"), "exam_notes" (list of revision sentences). '
        f"{sizes} Use only the material. Reply with JSON only.\n\nMaterial:\n{source}"
    )
    lists: Dict[str, Any] = {"key_concepts": [], "definitions": [], "exam_notes": []}
    for _ in range(2):  # one retry if the JSON is malformed
        raw = ollama_service.chat(
            [
                {"role": "system", "content": "You are StudyMate AI, a careful study assistant."},
                {"role": "user", "content": lists_prompt},
            ],
            json_mode=True,
            temperature=0.2,
            num_predict=600,
        )
        try:
            lists = _coerce_lists(extract_json(raw))
            break
        except ValueError:
            continue

    return {"summary": summary, **lists, "sections_total": len(sections), "sections_used": len(used)}


# ------------------------------------------------------- passages for quizzes
def _passages(chunks: Sequence[Dict[str, Any]], group: int = 2) -> List[Dict[str, Any]]:
    """Join consecutive chunks into passages (~1400 chars) that each remember their first page."""
    passages = []
    for i in range(0, len(chunks), group):
        part = chunks[i : i + group]
        text = "\n".join(c["text"] for c in part)
        if len(text) >= 80:
            passages.append({"text": text, "page_number": part[0]["page_number"]})
    return passages


def _items_from(raw: str) -> List[Any]:
    try:
        data = extract_json(raw)
    except ValueError:
        return []
    if isinstance(data, dict):
        for key in ("questions", "flashcards", "cards", "items"):
            if isinstance(data.get(key), list):
                return data[key]
        return [data]
    return data if isinstance(data, list) else []


# ----------------------------------------------------------------------- quiz
DIFFICULTY_HINTS = {
    "easy": "Ask direct recall questions about facts stated in the passage.",
    "medium": "Ask questions that need understanding of the passage, not just word matching.",
    "hard": "Ask questions that need reasoning or comparing ideas from the passage. Distractors must be plausible.",
}


def generate_quiz(chunks: Sequence[Dict[str, Any]], difficulty: str, count: int) -> Dict[str, Any]:
    passages = _passages(chunks)
    if not passages:
        raise AiGenerationError("The document does not contain enough text to build a quiz.")
    per_call = 1  # small models are far more reliable with one question per request
    calls_needed = math.ceil(count / per_call)
    order = pick_evenly(passages, calls_needed)

    questions: List[Dict[str, Any]] = []
    seen = set()
    attempts, max_attempts = 0, calls_needed * 2 + 2
    while len(questions) < count and attempts < max_attempts:
        passage = order[attempts % len(order)]
        attempts += 1
        want = min(per_call, count - len(questions))
        prompt = (
            f"Write {want} multiple-choice question based ONLY on this passage.\n"
            f"Difficulty: {difficulty}. {DIFFICULTY_HINTS[difficulty]}\n"
            "Reply with ONE JSON object and nothing else, exactly in this format:\n"
            '{"question": "...?", "options": ["first option", "second option", "third option", "fourth option"], '
            '"correct_index": 0, "explanation": "one sentence"}\n'
            "There must be exactly 4 different options. correct_index is the number 0, 1, 2 or 3 of the correct option.\n\n"
            f"Passage:\n{passage['text'][:1500]}"
        )
        raw = ollama_service.chat(
            [
                {"role": "system", "content": "You write accurate exam questions from study material. Reply with JSON only."},
                {"role": "user", "content": prompt},
            ],
            json_mode=True,
            temperature=0.4,
            num_predict=400,
        )
        for item in _items_from(raw):
            try:
                q = GeneratedQuestion.model_validate(normalize_question(item))
            except ValidationError as exc:
                log.warning("Rejected quiz question (%s). Raw model output: %r", exc.errors()[0].get("msg"), raw[:500])
                continue  # reject malformed question
            key = q.question.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            correct_text = q.options[q.correct_index]
            options = list(q.options)
            random.shuffle(options)  # models like to put the right answer first
            questions.append(
                {
                    "question": q.question.strip(),
                    "options": options,
                    "correct_index": options.index(correct_text),
                    "explanation": q.explanation.strip(),
                }
            )
            if len(questions) == count:
                break

    if not questions:
        raise AiGenerationError("The model did not produce any valid questions. Please try again.")
    warning = None
    if len(questions) < count:
        warning = f"Only {len(questions)} of {count} valid questions could be generated."
    return {"questions": questions, "warning": warning}


# ------------------------------------------------------------------ flashcards
def generate_flashcards(chunks: Sequence[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
    passages = _passages(chunks)
    if not passages:
        raise AiGenerationError("The document does not contain enough text to build flashcards.")
    per_call = 3
    calls_needed = math.ceil(count / per_call)
    order = pick_evenly(passages, calls_needed)

    cards: List[Dict[str, Any]] = []
    seen = set()
    attempts, max_attempts = 0, calls_needed * 2 + 2
    while len(cards) < count and attempts < max_attempts:
        passage = order[attempts % len(order)]
        attempts += 1
        want = min(per_call, count - len(cards))
        prompt = (
            f"Write {want} study flashcard(s) based ONLY on this passage. Each has a clear question, "
            "a short accurate answer and a key concept (2-4 words).\n"
            'Reply with JSON only: {"flashcards": [{"question": "...", "answer": "...", "key_concept": "..."}]}\n\n'
            f"Passage:\n{passage['text']}"
        )
        raw = ollama_service.chat(
            [
                {"role": "system", "content": "You create accurate flashcards from study material. Reply with JSON only."},
                {"role": "user", "content": prompt},
            ],
            json_mode=True,
            temperature=0.4,
            num_predict=600,
        )
        for item in _items_from(raw):
            try:
                card = GeneratedCard.model_validate(normalize_card(item))
            except ValidationError as exc:
                log.warning("Rejected flashcard (%s). Raw model output: %r", exc.errors()[0].get("msg"), raw[:500])
                continue
            key = card.question.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            cards.append(
                {
                    "question": card.question.strip(),
                    "answer": card.answer.strip(),
                    "key_concept": card.key_concept.strip(),
                    "source_page": passage["page_number"],
                }
            )
            if len(cards) == count:
                break

    if not cards:
        raise AiGenerationError("The model did not produce any valid flashcards. Please try again.")
    return cards