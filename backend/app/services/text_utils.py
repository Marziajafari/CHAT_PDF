"""Pure text helpers (no heavy dependencies, easy to unit test)."""
import json
import re
from typing import Any, Dict, List, Sequence, Tuple
 
 
def clean_text(text: str) -> str:
    """Normalise whitespace from PDF extraction while keeping paragraph breaks."""
    text = text.replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"-\n(\w)", r"\1", text)  # re-join words hyphenated at line ends
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)  # single line breaks -> space
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
 
 
def chunk_text(text: str, size: int = 700, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks, preferring to cut at sentence/word boundaries."""
    text = clean_text(text)
    if not text:
        return []
    if size < 50:
        size = 50
    if overlap < 0 or overlap >= size:
        overlap = size // 7
    chunks: List[str] = []
    n = len(text)
    start = 0
    while start < n:
        end = min(start + size, n)
        if end < n:
            window_start = start + int(size * 0.6)
            cut = max(text.rfind(". ", window_start, end), text.rfind("\n", window_start, end))
            if cut == -1:
                cut = text.rfind(" ", window_start, end)
            if cut != -1 and cut + 1 > start:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks
 
 
def chunk_pages(
    pages: Sequence[Tuple[int, str]], size: int = 700, overlap: int = 100
) -> List[Dict[str, Any]]:
    """Chunk page by page so every chunk keeps the page number it came from."""
    result: List[Dict[str, Any]] = []
    index = 0
    for page_number, text in pages:
        for piece in chunk_text(text, size, overlap):
            result.append({"page_number": page_number, "chunk_index": index, "text": piece})
            index += 1
    return result
 
 
def extract_json(raw: str) -> Any:
    """Parse JSON from model output, tolerating code fences and surrounding prose."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    fenced = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(fenced)
    except json.JSONDecodeError:
        pass
    first, last = raw.find("{"), raw.rfind("}")
    if first != -1 and last > first:
        try:
            return json.loads(raw[first : last + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError("No valid JSON found in model output.")
 
 
def pick_evenly(items: Sequence[Any], k: int) -> List[Any]:
    """Pick up to k items spread evenly across the sequence (keeps order, no repeats)."""
    n = len(items)
    if k <= 0 or n == 0:
        return []
    if k >= n:
        return list(items)
    if k == 1:
        return [items[n // 2]]
    indices: List[int] = []
    for i in range(k):
        idx = round(i * (n - 1) / (k - 1))
        if idx not in indices:
            indices.append(idx)
    return [items[i] for i in indices]
 
 
# ---------------------------------------------------------------- tolerant LLM output readers
_PREFIX = re.compile(r"^\s*(?:\(?[A-Da-d][\)\.:]|\d[\)\.])\s*")
 
 
def _clean_option(value: Any) -> str:
    return _PREFIX.sub("", str(value)).strip()
 
 
def _find_index(d: Dict[str, Any], options: List[str], letters: List[str]) -> Any:
    """Work out which option is correct from the many shapes small models produce."""
    for key in ("correct_index", "correct_answer", "answer", "correct", "correct_option", "right_answer"):
        if key not in d or d[key] is None:
            continue
        value = d[key]
        if isinstance(value, bool):
            continue
        if isinstance(value, int) or (isinstance(value, str) and value.strip().isdigit()):
            n = int(value)
            if 0 <= n <= 3:
                return n
            if n == 4:
                return 3
            continue
        text = str(value).strip()
        match = re.match(r"^(?:option\s*)?\(?([A-D])\)?(?:[\.:\)]|$)", text, re.IGNORECASE)
        if match:
            return "ABCD".index(match.group(1).upper())
        if letters and text in letters:
            return letters.index(text)
        wanted = _clean_option(text).lower()
        for i, opt in enumerate(options):
            if opt.lower() == wanted:
                return i
    return None
 
 
def normalize_question(item: Any) -> Any:
    """Turn the many shapes a small model returns into the exact shape we validate."""
    if not isinstance(item, dict):
        return item
    d = {str(k).lower(): v for k, v in item.items()}
    question = d.get("question") or d.get("q") or d.get("text") or ""
    raw_options = d.get("options") or d.get("choices") or d.get("answers") or d.get("answer_options")
    letters: List[str] = []
    if isinstance(raw_options, dict):
        letters = [str(k) for k in raw_options.keys()]
        raw_options = list(raw_options.values())
    options = [_clean_option(o) for o in raw_options] if isinstance(raw_options, list) else []
    result: Dict[str, Any] = {
        "question": str(question).strip(),
        "options": options,
        "explanation": str(d.get("explanation") or d.get("reason") or d.get("rationale") or "See the passage.").strip(),
    }
    index = _find_index(d, options, letters)
    if index is not None:
        result["correct_index"] = index
    return result
 
 
def normalize_card(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    d = {str(k).lower(): v for k, v in item.items()}
    question = d.get("question") or d.get("front") or d.get("q") or d.get("term") or ""
    answer = d.get("answer") or d.get("back") or d.get("a") or d.get("definition") or ""
    concept = d.get("key_concept") or d.get("concept") or d.get("topic") or d.get("term") or ""
    return {"question": str(question).strip(), "answer": str(answer).strip(), "key_concept": str(concept).strip()[:120]}