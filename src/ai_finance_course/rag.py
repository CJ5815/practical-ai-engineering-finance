"""Basic retrieval-augmented generation: Week 9's retrieval + Weeks 6-7's prompting/validation.

The LLM call is injected as `generate: Callable[[str], str]` — the same
pattern as ai_finance_course.skills.value_investor (Week 17) — so this
module never imports an LLM SDK or calls the network itself. Retrieval
(query_collection) is fully deterministic; only the answer's wording comes
from the LLM (CLAUDE.md-style rule: LLM for synthesis, not for facts).
"""

from __future__ import annotations

import json
from collections.abc import Callable

from chromadb.api.models.Collection import Collection
from pydantic import BaseModel

from ai_finance_course.json_utils import extract_json
from ai_finance_course.vector_store import query_collection


class RAGAnswer(BaseModel):
    """A grounded answer, with citations back to the retrieved evidence used."""

    answer: str
    citations: list[int]
    """1-based indices into the evidence list passed to build_grounded_prompt."""


def build_grounded_prompt(query: str, evidence: list[dict]) -> str:
    """Build a role/task/evidence/constraints/output-format prompt (Week 6's structure).

    Args:
        query: The user's question.
        evidence: Retrieved chunks from query_collection, each a
            {"text", "metadata", "distance"} dict.

    Returns:
        A complete prompt asking the model to answer using only the
        numbered evidence, and to cite which numbers it used.
    """
    evidence_block = "\n".join(
        f"[{i + 1}] ({chunk['metadata'].get('ticker', 'unknown')}, "
        f"{chunk['metadata'].get('doc_type', 'unknown')}): {chunk['text']}"
        for i, chunk in enumerate(evidence)
    )

    return f"""ROLE: You are a financial research assistant who answers questions using \
only the evidence provided, and always cites which evidence you used.

TASK: Answer the question below using only the evidence.

QUESTION: {query}

EVIDENCE:
{evidence_block}

CONSTRAINTS:
- Base your answer only on the evidence above. Do not invent facts.
- "citations" must list the number(s) of every evidence item you actually used to \
answer, and nothing else.
- If none of the evidence is relevant to the question, say so explicitly in the \
answer and return an empty citations list.

OUTPUT FORMAT: Return ONLY valid JSON, no other text, matching this shape:
{{"answer": "one or two sentences", "citations": [1, 2]}}"""


def answer_question(
    query: str,
    collection: Collection,
    generate: Callable[[str], str],
    n_results: int = 3,
    where: dict | None = None,
) -> tuple[RAGAnswer, list[dict]]:
    """Retrieve relevant evidence and generate a grounded, cited answer.

    Args:
        query: The user's question.
        collection: A ChromaDB collection from vector_store.get_or_create_collection.
        generate: A function that takes a prompt and returns the LLM's raw
            text response. Injected so this function never calls a
            provider's API directly.
        n_results: How many chunks to retrieve as evidence.
        where: Optional metadata filter passed through to query_collection.

    Returns:
        A tuple of (the validated RAGAnswer, the evidence chunks actually
        retrieved) — returning the real evidence alongside the answer means
        a caller can map citation numbers back to real sources without
        trusting the model's own account of what evidence exists.

    Raises:
        pydantic.ValidationError: If the LLM's response doesn't match the
            expected shape (a subclass of ValueError — Week 7 §3.3).
        ValueError: If the LLM cites an evidence number that doesn't exist
            (e.g. citing [5] when only 3 chunks were retrieved) — caught
            here rather than left to crash whatever maps citations back to
            evidence later.
    """
    evidence = query_collection(collection, query, n_results=n_results, where=where)
    prompt = build_grounded_prompt(query, evidence)
    raw_response = generate(prompt)
    parsed = json.loads(extract_json(raw_response))
    answer = RAGAnswer(**parsed)

    out_of_range = [c for c in answer.citations if not (1 <= c <= len(evidence))]
    if out_of_range:
        raise ValueError(
            f"Model cited evidence number(s) {out_of_range}, but only {len(evidence)} "
            "evidence chunks were retrieved."
        )

    return answer, evidence
