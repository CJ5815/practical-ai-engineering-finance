"""Tests for the Week 16 capstone dataset — data/sample/capstone_passages.json
and data/sample/capstone_eval_questions.json.

No embedding model or LLM involved: these check the data files themselves
are internally consistent, which is exactly what would silently break if
someone edited capstone_passages.json's wording without updating the
matching relevant_texts in capstone_eval_questions.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_finance_course.chunking import chunk_document

PASSAGES_PATH = Path("data/sample/capstone_passages.json")
QUESTIONS_PATH = Path("data/sample/capstone_eval_questions.json")


def test_capstone_passages_cover_at_least_three_companies() -> None:
    passages = json.loads(PASSAGES_PATH.read_text(encoding="utf-8"))

    tickers = {passage["ticker"] for passage in passages}
    assert len(tickers) >= 3
    assert all({"ticker", "doc_type", "text"} <= passage.keys() for passage in passages)


def test_capstone_eval_questions_has_at_least_fifteen_entries() -> None:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))

    assert len(questions) >= 15
    assert all({"query", "expected_ticker", "relevant_texts"} <= question.keys() for question in questions)


def test_capstone_eval_questions_relevant_texts_exist_in_passages() -> None:
    """Catches a typo or edit in either file that would silently make
    recall_at_k/precision_at_k (Week 12) always score a question as a miss."""
    passages = json.loads(PASSAGES_PATH.read_text(encoding="utf-8"))
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))

    passage_texts = {passage["text"] for passage in passages}
    for question in questions:
        for relevant_text in question["relevant_texts"]:
            assert relevant_text in passage_texts, f"{relevant_text!r} not found in capstone_passages.json"


def test_capstone_eval_questions_expected_ticker_matches_relevant_passage() -> None:
    passages = json.loads(PASSAGES_PATH.read_text(encoding="utf-8"))
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))

    ticker_by_text = {passage["text"]: passage["ticker"] for passage in passages}
    for question in questions:
        for relevant_text in question["relevant_texts"]:
            assert ticker_by_text[relevant_text] == question["expected_ticker"]


def test_capstone_passages_each_chunk_into_exactly_one_chunk() -> None:
    """Each passage is short enough that chunk_document should never split
    it — if this ever fails, capstone_eval_questions.json's relevant_texts
    (which match whole-passage text) would stop matching individual chunks."""
    passages = json.loads(PASSAGES_PATH.read_text(encoding="utf-8"))

    for passage in passages:
        chunks = chunk_document(passage["text"], {"ticker": passage["ticker"]}, chunk_size=500, overlap=50)
        assert len(chunks) == 1
        assert chunks[0]["text"] == passage["text"]
