import pytest

from app.services.text_utils import chunk_pages, chunk_text, clean_text, extract_json, pick_evenly


def test_clean_text_joins_lines_and_hyphens():
    assert clean_text("learn-\ning is   fun\nreally") == "learning is fun really"


def test_chunk_sizes_and_overlap():
    text = " ".join(f"word{i}" for i in range(400))  # ~2.5k characters
    chunks = chunk_text(text, size=700, overlap=100)
    assert len(chunks) > 3
    assert all(len(c) <= 700 for c in chunks)
    # consecutive chunks share some text (overlap)
    assert chunks[0][-30:].split()[-1] in chunks[1]


def test_chunk_text_empty_and_short():
    assert chunk_text("   ") == []
    assert chunk_text("Short text.") == ["Short text."]


def test_chunk_pages_keeps_page_numbers_and_sequential_index():
    pages = [(1, "Alpha " * 200), (2, "Beta " * 200)]
    chunks = chunk_pages(pages, size=300, overlap=50)
    assert {c["page_number"] for c in chunks} == {1, 2}
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))
    assert all("Beta" not in c["text"] for c in chunks if c["page_number"] == 1)


def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert extract_json('Sure! Here it is: {"a": 3} hope it helps') == {"a": 3}
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_pick_evenly():
    assert pick_evenly(list(range(10)), 3) == [0, 4, 9] or len(pick_evenly(list(range(10)), 3)) == 3
    assert pick_evenly([1, 2], 5) == [1, 2]
    assert pick_evenly([], 3) == []
