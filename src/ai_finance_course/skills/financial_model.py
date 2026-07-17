"""Philosophy-agnostic ratio analysis over a FinancialStatements snapshot.

Every function here is pure — no file I/O, no network — following the
same style as ai_finance_course.analysis. Any future investment
philosophy skill can reuse these without duplicating the math.
"""

from __future__ import annotations

from ai_finance_course.skills.base import FinancialStatements


def current_ratio(financials: FinancialStatements) -> float:
    """Liquidity: can short-term assets cover short-term liabilities?"""
    return financials.current_assets / financials.current_liabilities


def debt_to_equity(financials: FinancialStatements) -> float:
    """Leverage: how much debt/liability financing per dollar of equity."""
    return financials.total_liabilities / financials.total_equity


def return_on_equity(financials: FinancialStatements) -> float:
    """Profitability: net income earned per dollar of shareholder equity."""
    return financials.net_income / financials.total_equity


def return_on_assets(financials: FinancialStatements) -> float:
    """Profitability: net income earned per dollar of total assets."""
    return financials.net_income / financials.total_assets


def net_margin(financials: FinancialStatements) -> float:
    """Profitability: net income as a share of revenue."""
    return financials.net_income / financials.revenue


def calculate_all_ratios(financials: FinancialStatements) -> dict[str, float]:
    """Calculate every ratio at once, keyed by name, for InvestmentThesis.ratios."""
    return {
        "current_ratio": current_ratio(financials),
        "debt_to_equity": debt_to_equity(financials),
        "return_on_equity": return_on_equity(financials),
        "return_on_assets": return_on_assets(financials),
        "net_margin": net_margin(financials),
    }
