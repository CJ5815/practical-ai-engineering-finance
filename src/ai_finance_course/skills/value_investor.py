"""The Value Investor skill: a Graham/Buffett-style process for evaluating a stock.

Combines retrieved evidence, ratio analysis (financial_model.py), and DCF
valuation (dcf_model.py) into one LLM prompt, then validates the response
into a structured InvestmentThesis.

The LLM call itself is injected as `generate: Callable[[str], str]` — this
module never imports an LLM SDK or calls the network directly, so it's
testable with a stub (tests/test_value_investor.py) and reusable with
whatever provider a caller wires up (examples/week-17/evaluate_company.py
calls Anthropic's API directly via httpx).
"""

from __future__ import annotations

import json
import textwrap
from collections.abc import Callable

from matplotlib.figure import Figure
from matplotlib import pyplot as plt

from ai_finance_course.skills.base import Catalyst, EvidenceChunk, FinancialStatements, InvestmentThesis
from ai_finance_course.skills.dcf_model import DCFAssumptions, intrinsic_value_per_share, margin_of_safety_pct
from ai_finance_course.skills.financial_model import calculate_all_ratios

PHILOSOPHY_NAME = "Value Investing (Graham/Buffett)"


def build_prompt(
    ticker: str,
    evidence: list[EvidenceChunk],
    ratios: dict[str, float],
    intrinsic_value: float,
    current_price: float,
    margin_of_safety: float,
) -> str:
    """Build the evidence-based prompt for the value-investor evaluation.

    Follows Week 6's role/task/evidence/constraints/output-format structure.
    """
    evidence_block = "\n".join(f"[{i + 1}] ({e.source}): {e.text}" for i, e in enumerate(evidence))
    ratios_block = "\n".join(f"- {name}: {value:.4f}" for name, value in ratios.items())

    return f"""ROLE: You are a value investor in the tradition of Benjamin Graham and \
Warren Buffett. You prioritize a durable business, financial strength, and buying \
below intrinsic value with a margin of safety.

TASK: Evaluate {ticker} and produce an investment thesis based only on the evidence \
and numbers below.

EVIDENCE:
{evidence_block}

FINANCIAL RATIOS:
{ratios_block}

VALUATION:
- Intrinsic value per share (DCF): {intrinsic_value:.2f}
- Current share price: {current_price:.2f}
- Margin of safety: {margin_of_safety:.2%}

CONSTRAINTS:
- Base every claim only on the evidence and numbers above. Do not invent facts.
- List catalysts in chronological order, nearest-term first.
- Each catalyst must be a specific, dated-or-timeframed event, not a vague trend.

OUTPUT FORMAT: Return ONLY valid JSON, no other text, matching this shape:
{{
  "thesis_summary": "one paragraph",
  "bull_case": ["reason 1", "reason 2", "..."],
  "bear_case": ["reason 1", "reason 2", "..."],
  "catalysts": [
    {{"description": "...", "timeframe": "e.g. Q1 2027", "direction": "bull"}},
    {{"description": "...", "timeframe": "e.g. FY2028", "direction": "bear"}}
  ]
}}"""


def _extract_json(text: str) -> str:
    """Strip a ```json fence around the response, if the LLM added one."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.removeprefix("json").strip()
    return stripped


def evaluate_company(
    ticker: str,
    evidence: list[EvidenceChunk],
    financials: FinancialStatements,
    dcf_assumptions: DCFAssumptions,
    generate: Callable[[str], str],
) -> InvestmentThesis:
    """Evaluate a company as a value investor would.

    Args:
        ticker: The company's stock ticker.
        evidence: Retrieved evidence chunks (e.g. from a student's own RAG pipeline).
        financials: A structured snapshot of the company's financial statements.
        dcf_assumptions: Assumptions for the DCF valuation.
        generate: A function that takes a prompt and returns the LLM's raw
            text response. Injected so this function never calls a
            network/LLM SDK itself — tests pass a stub, real callers wire
            up a real provider (see examples/week-17/evaluate_company.py).

    Returns:
        A validated InvestmentThesis.

    Raises:
        pydantic.ValidationError: If the LLM's response doesn't match the
            expected shape.
    """
    ratios = calculate_all_ratios(financials)
    intrinsic_value = intrinsic_value_per_share(dcf_assumptions)
    margin = margin_of_safety_pct(intrinsic_value, dcf_assumptions.current_share_price)

    prompt = build_prompt(
        ticker, evidence, ratios, intrinsic_value, dcf_assumptions.current_share_price, margin
    )
    raw_response = generate(prompt)
    parsed = json.loads(_extract_json(raw_response))

    return InvestmentThesis(
        company=ticker,
        philosophy=PHILOSOPHY_NAME,
        thesis_summary=parsed["thesis_summary"],
        bull_case=parsed["bull_case"],
        bear_case=parsed["bear_case"],
        catalysts=[Catalyst(**c) for c in parsed["catalysts"]],
        ratios=ratios,
        intrinsic_value_per_share=intrinsic_value,
        current_price=dcf_assumptions.current_share_price,
        margin_of_safety_pct=margin,
    )


def render_catalyst_timeline(thesis: InvestmentThesis) -> Figure:
    """Plot catalysts along a time axis: bull catalysts above the line, bear below.

    Assumes thesis.catalysts is already in chronological order (the prompt
    instructs the LLM to return it that way).
    """
    width = max(10, len(thesis.catalysts) * 2.5)
    fig, ax = plt.subplots(figsize=(width, 5))
    ax.axhline(0, color="black", linewidth=1)

    # Stagger each side's annotations further from the line in turn, so
    # catalysts close together in time don't overlap each other's text.
    bull_count = 0
    bear_count = 0
    for i, catalyst in enumerate(thesis.catalysts):
        is_bull = catalyst.direction == "bull"
        y = 1 if is_bull else -1
        color = "#2a9d3f" if is_bull else "#d9534f"
        level = bull_count if is_bull else bear_count
        offset = (15 + level * 45) if is_bull else -(20 + level * 45)
        if is_bull:
            bull_count += 1
        else:
            bear_count += 1

        ax.plot([i, i], [0, y], color=color, linewidth=2)
        ax.scatter([i], [y], color=color, zorder=3)
        ax.annotate(
            textwrap.fill(catalyst.description, width=28),
            xy=(i, y),
            xytext=(0, offset),
            textcoords="offset points",
            ha="center",
            va="bottom" if is_bull else "top",
            fontsize=8,
        )

    ax.set_xticks(range(len(thesis.catalysts)))
    ax.set_xticklabels([c.timeframe for c in thesis.catalysts], rotation=30, ha="right")
    ax.set_yticks([])
    max_level = max(bull_count, bear_count, 1)
    ax.set_ylim(-2 - 0.6 * max_level, 2 + 0.6 * max_level)
    ax.set_title(f"{thesis.company} — Catalyst Timeline (bull above, bear below)")
    fig.tight_layout()
    return fig
