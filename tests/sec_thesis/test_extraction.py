import json

import pytest

from sec_thesis.llm.extraction import ExtractionResult, extract_relationships

SAMPLE_RESPONSE = json.dumps(
    {
        "entities": [
            {"name": "Apple Inc.", "entity_type": "company", "ticker": "AAPL"},
            {"name": "Samsung Electronics", "entity_type": "company", "ticker": None},
        ],
        "relationships": [
            {
                "source": "Apple Inc.",
                "target": "Samsung Electronics",
                "relation_type": "competitor_of",
                "evidence": "we compete with Samsung Electronics",
            }
        ],
    }
)


def test_extract_relationships_parses_valid_response() -> None:
    def stub_generate(prompt: str) -> str:
        return SAMPLE_RESPONSE

    result = extract_relationships("AAPL", "we compete with Samsung Electronics", stub_generate)

    assert isinstance(result, ExtractionResult)
    assert len(result.entities) == 2
    assert result.relationships[0].relation_type == "competitor_of"


def test_extract_relationships_strips_markdown_fence() -> None:
    def stub_generate(prompt: str) -> str:
        return f"```json\n{SAMPLE_RESPONSE}\n```"

    result = extract_relationships("AAPL", "we compete with Samsung Electronics", stub_generate)

    assert len(result.entities) == 2


def test_extract_relationships_rejects_invalid_relation_type() -> None:
    bad_response = json.dumps(
        {
            "entities": [{"name": "Apple Inc.", "entity_type": "company", "ticker": "AAPL"}],
            "relationships": [
                {
                    "source": "Apple Inc.",
                    "target": "Someone",
                    "relation_type": "partners_with",  # not a valid Literal value
                    "evidence": "...",
                }
            ],
        }
    )

    def stub_generate(prompt: str) -> str:
        return bad_response

    with pytest.raises(ValueError):
        extract_relationships("AAPL", "text", stub_generate)


def test_build_prompt_includes_ticker_and_text() -> None:
    from sec_thesis.llm.extraction import build_prompt

    prompt = build_prompt("AAPL", "sample filing text")

    assert "AAPL" in prompt
    assert "sample filing text" in prompt
