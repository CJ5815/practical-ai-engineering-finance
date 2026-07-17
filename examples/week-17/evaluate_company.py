"""Week 17: run the Value Investor skill end to end.

Requires LLM_API_KEY and LLM_MODEL in a .env file (see .env.example) —
this script calls a real LLM (Anthropic's Messages API, via a direct
httpx POST, no SDK) to produce the thesis.

The evidence and financials below are illustrative sample data for a
fictional "DEMO Corp" (the same DEMO ticker used in data/sample/prices.csv
since Week 1) — not a real company's real numbers. evaluate_company()
itself is provider-agnostic; only _call_llm below is Anthropic-specific.

Run this file directly:

    python examples/week-17/evaluate_company.py
"""

from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

from ai_finance_course.skills.base import EvidenceChunk, FinancialStatements
from ai_finance_course.skills.dcf_model import DCFAssumptions, build_dcf_workbook
from ai_finance_course.skills.value_investor import evaluate_company, render_catalyst_timeline

TICKER = "DEMO"

# Illustrative sample data, not a real company's real filings/financials.
EVIDENCE = [
    EvidenceChunk(
        text=(
            "DEMO Corp's 10-K reports steady revenue growth over the past three years, "
            "driven by expansion into two new regional markets."
        ),
        source="10-K, Item 7",
    ),
    EvidenceChunk(
        text="Management highlighted rising input costs as a margin headwind for the coming year.",
        source="Earnings call transcript",
    ),
]

FINANCIALS = FinancialStatements(
    revenue=1_000_000.0,
    net_income=100_000.0,
    total_assets=2_000_000.0,
    total_liabilities=800_000.0,
    total_equity=1_200_000.0,
    current_assets=500_000.0,
    current_liabilities=250_000.0,
)

DCF_ASSUMPTIONS = DCFAssumptions(
    base_revenue=1_000_000.0,
    revenue_growth_rates=[0.08, 0.07, 0.06, 0.05, 0.04],
    ebit_margin=0.20,
    tax_rate=0.25,
    da_pct_revenue=0.05,
    capex_pct_revenue=0.06,
    nwc_change_pct_revenue=0.01,
    wacc=0.10,
    terminal_growth_rate=0.03,
    shares_outstanding=100_000.0,
    net_debt=200_000.0,
    current_share_price=15.0,
)

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


def _call_llm(prompt: str) -> str:
    """Call Anthropic's Messages API directly via httpx (no SDK dependency).

    This is the one Anthropic-specific piece — evaluate_company() itself
    just takes a generate: Callable[[str], str], so swapping providers
    means writing a different small function like this one.
    """
    api_key = os.environ["LLM_API_KEY"]
    model = os.environ["LLM_MODEL"]

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            ANTHROPIC_MESSAGES_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                # Generous budget: some models think before answering, and
                # that counts against max_tokens too — too low truncates
                # the actual JSON response before it's complete.
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()

        # Some models include a "thinking" block before the "text" block —
        # find the text block by type rather than assuming content[0].
        for block in data["content"]:
            if block["type"] == "text":
                return block["text"]
        raise ValueError(f"No text block in response: {data}")


def main() -> None:
    load_dotenv()

    thesis = evaluate_company(TICKER, EVIDENCE, FINANCIALS, DCF_ASSUMPTIONS, generate=_call_llm)

    print(f"=== {thesis.company}: {thesis.philosophy} ===\n")
    print(thesis.thesis_summary, "\n")

    print("Bull case:")
    for reason in thesis.bull_case:
        print(f"  + {reason}")

    print("\nBear case:")
    for reason in thesis.bear_case:
        print(f"  - {reason}")

    print(f"\nIntrinsic value per share: ${thesis.intrinsic_value_per_share:.2f}")
    print(f"Current price: ${thesis.current_price:.2f}")
    print(f"Margin of safety: {thesis.margin_of_safety_pct:.1%}")

    figure = render_catalyst_timeline(thesis)
    figure.savefig("catalyst_timeline.png", dpi=150)
    print("\nSaved catalyst timeline to catalyst_timeline.png")

    build_dcf_workbook(DCF_ASSUMPTIONS, "dcf_model.xlsx")
    print("Saved DCF model to dcf_model.xlsx")


if __name__ == "__main__":
    main()
