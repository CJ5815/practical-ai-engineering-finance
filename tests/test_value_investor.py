import json

import matplotlib
import pytest

matplotlib.use("Agg")  # headless backend for tests — no window, no display needed

from ai_finance_course.skills.base import EvidenceChunk, FinancialStatements
from ai_finance_course.skills.dcf_model import DCFAssumptions, intrinsic_value_per_share, margin_of_safety_pct
from ai_finance_course.skills.value_investor import (
    build_prompt,
    evaluate_company,
    render_catalyst_timeline,
)

FINANCIALS = FinancialStatements(
    revenue=1000.0,
    net_income=100.0,
    total_assets=2000.0,
    total_liabilities=800.0,
    total_equity=1200.0,
    current_assets=500.0,
    current_liabilities=250.0,
)

DCF_ASSUMPTIONS = DCFAssumptions(
    base_revenue=1000.0,
    revenue_growth_rates=[0.10, 0.10],
    ebit_margin=0.20,
    tax_rate=0.25,
    da_pct_revenue=0.05,
    capex_pct_revenue=0.06,
    nwc_change_pct_revenue=0.01,
    wacc=0.10,
    terminal_growth_rate=0.03,
    shares_outstanding=100.0,
    net_debt=200.0,
    current_share_price=15.0,
)

EVIDENCE = [EvidenceChunk(text="Revenue grew 10% year over year.", source="10-K")]

CANNED_RESPONSE = {
    "thesis_summary": "A financially strong company trading below intrinsic value.",
    "bull_case": ["Consistent revenue growth", "Strong balance sheet"],
    "bear_case": ["Margin pressure from competition"],
    "catalysts": [
        {"description": "Q1 earnings beat", "timeframe": "Q1 2027", "direction": "bull"},
        {"description": "New competitor product launch", "timeframe": "FY2028", "direction": "bear"},
    ],
}


def test_build_prompt_includes_evidence_and_ratios() -> None:
    prompt = build_prompt("DEMO", EVIDENCE, {"current_ratio": 2.0}, 20.0, 15.0, 0.25)

    assert "DEMO" in prompt
    assert "Revenue grew 10% year over year." in prompt
    assert "current_ratio: 2.0000" in prompt
    assert "Margin of safety: 25.00%" in prompt


def test_evaluate_company_with_stub() -> None:
    def stub_generate(prompt: str) -> str:
        return json.dumps(CANNED_RESPONSE)

    thesis = evaluate_company("DEMO", EVIDENCE, FINANCIALS, DCF_ASSUMPTIONS, stub_generate)

    assert thesis.company == "DEMO"
    assert thesis.bull_case == CANNED_RESPONSE["bull_case"]
    assert thesis.bear_case == CANNED_RESPONSE["bear_case"]
    assert len(thesis.catalysts) == 2
    assert thesis.catalysts[0].direction == "bull"
    assert thesis.intrinsic_value_per_share == pytest.approx(intrinsic_value_per_share(DCF_ASSUMPTIONS))
    assert thesis.margin_of_safety_pct == pytest.approx(
        margin_of_safety_pct(intrinsic_value_per_share(DCF_ASSUMPTIONS), DCF_ASSUMPTIONS.current_share_price)
    )


def test_evaluate_company_strips_json_code_fence() -> None:
    def stub_generate(prompt: str) -> str:
        return "```json\n" + json.dumps(CANNED_RESPONSE) + "\n```"

    thesis = evaluate_company("DEMO", EVIDENCE, FINANCIALS, DCF_ASSUMPTIONS, stub_generate)

    assert thesis.thesis_summary == CANNED_RESPONSE["thesis_summary"]


def test_render_catalyst_timeline() -> None:
    def stub_generate(prompt: str) -> str:
        return json.dumps(CANNED_RESPONSE)

    thesis = evaluate_company("DEMO", EVIDENCE, FINANCIALS, DCF_ASSUMPTIONS, stub_generate)

    figure = render_catalyst_timeline(thesis)

    assert [t.get_text() for t in figure.axes[0].get_xticklabels()] == ["Q1 2027", "FY2028"]
