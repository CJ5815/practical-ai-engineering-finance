"""Shared types for investment philosophy skills.

These types are philosophy-agnostic: every skill (value_investor.py, and
future philosophies) builds an InvestmentThesis out of the same building
blocks, so adding a new philosophy later means writing a new prompt and
evaluation function, not new infrastructure.
"""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel


class EvidenceChunk(BaseModel):
    """One piece of retrieved evidence about a company.

    This is deliberately generic: it's whatever a student's own RAG
    pipeline (Weeks 9-11) already retrieved, not something this module
    fetches itself.
    """

    text: str
    source: str


class FinancialStatements(BaseModel):
    """A structured snapshot of a company's key financial statement line items.

    This is the "model of financial statements" for ratio analysis
    (financial_model.py) and the base year for the DCF (dcf_model.py) —
    a typed representation, not a multi-year projection by itself.
    """

    revenue: float
    net_income: float
    total_assets: float
    total_liabilities: float
    total_equity: float
    current_assets: float
    current_liabilities: float


class Catalyst(BaseModel):
    """A specific, dated event that could move the stock, one way or the other."""

    description: str
    timeframe: str
    direction: Literal["bull", "bear"]


class InvestmentThesis(BaseModel):
    """The full output of evaluating a company under one investment philosophy."""

    company: str
    philosophy: str
    thesis_summary: str
    bull_case: list[str]
    bear_case: list[str]
    catalysts: list[Catalyst]
    ratios: dict[str, float]
    intrinsic_value_per_share: float | None = None
    current_price: float | None = None
    margin_of_safety_pct: float | None = None


class InvestmentPhilosophy(Protocol):
    """The interface every investment philosophy skill implements."""

    def evaluate(
        self,
        ticker: str,
        evidence: list[EvidenceChunk],
        financials: FinancialStatements,
    ) -> InvestmentThesis:
        """Evaluate a company and return a full investment thesis."""
        ...
