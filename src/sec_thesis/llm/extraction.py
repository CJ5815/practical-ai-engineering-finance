"""Extract entities and relationships from filing text using an LLM.

The LLM call is injected as `generate: Callable[[str], str]` — same pattern
as ai_finance_course.skills.value_investor (Week 17) — so this module never
imports an LLM SDK or calls the network itself. Tests pass a stub; real
callers wire up a real provider (see examples/week-20/build_company_graph.py).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel


class Entity(BaseModel):
    """A node in the knowledge graph: a company or a person."""

    name: str
    entity_type: Literal["company", "person"]
    ticker: str | None = None


class Relationship(BaseModel):
    """A directed, evidenced edge between two entities (by name)."""

    source: str
    target: str
    relation_type: Literal["competitor_of", "subsidiary_of", "executive_of", "supplier_of"]
    evidence: str
    """A short snippet from the filing text supporting this relationship (CLAUDE.md rule 4)."""


class ExtractionResult(BaseModel):
    """Everything extracted from one filing's text."""

    entities: list[Entity]
    relationships: list[Relationship]


def build_prompt(ticker: str, filing_text: str) -> str:
    """Build the extraction prompt.

    Follows Week 6's role/task/evidence/constraints/output-format structure,
    same as ai_finance_course.skills.value_investor.build_prompt (Week 17).
    """
    return f"""ROLE: You are an information-extraction analyst reading SEC filing \
text to build a knowledge graph of company relationships.

TASK: Read the filing text below for {ticker} and extract every company and \
person it names, along with the relationships between them.

FILING TEXT:
{filing_text}

CONSTRAINTS:
- Only extract entities and relationships explicitly stated in the text above. \
Do not invent facts (CLAUDE.md rule 3).
- relation_type must be exactly one of: competitor_of, subsidiary_of, \
executive_of, supplier_of.
- Each relationship's "evidence" field must be a short snippet copied from the \
text above, not a paraphrase (CLAUDE.md rule 4).
- If the text names no clear relationships, return empty lists rather than guessing.

OUTPUT FORMAT: Return ONLY valid JSON, no other text, matching this shape:
{{
  "entities": [
    {{"name": "...", "entity_type": "company", "ticker": "..." }},
    {{"name": "...", "entity_type": "person", "ticker": null}}
  ],
  "relationships": [
    {{"source": "...", "target": "...", "relation_type": "competitor_of", \
"evidence": "..."}}
  ]
}}"""


def _extract_json(text: str) -> str:
    """Strip a ```json fence around the response, if the LLM added one."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.removeprefix("json").strip()
    return stripped


def extract_relationships(ticker: str, filing_text: str, generate: Callable[[str], str]) -> ExtractionResult:
    """Extract entities and relationships from a filing's text.

    Args:
        ticker: The filing company's ticker (for prompt context).
        filing_text: Plain text from filing_parser.extract_text.
        generate: A function that takes a prompt and returns the LLM's raw
            text response.

    Returns:
        A validated ExtractionResult.

    Raises:
        pydantic.ValidationError: If the LLM's response doesn't match the
            expected shape.
    """
    prompt = build_prompt(ticker, filing_text)
    raw_response = generate(prompt)
    parsed = json.loads(_extract_json(raw_response))
    return ExtractionResult(**parsed)
