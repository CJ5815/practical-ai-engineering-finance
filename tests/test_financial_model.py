import pytest

from ai_finance_course.skills.base import FinancialStatements
from ai_finance_course.skills.financial_model import (
    calculate_all_ratios,
    current_ratio,
    debt_to_equity,
    net_margin,
    return_on_assets,
    return_on_equity,
)

SAMPLE = FinancialStatements(
    revenue=1000.0,
    net_income=100.0,
    total_assets=2000.0,
    total_liabilities=800.0,
    total_equity=1200.0,
    current_assets=500.0,
    current_liabilities=250.0,
)


def test_current_ratio() -> None:
    assert current_ratio(SAMPLE) == pytest.approx(2.0)


def test_debt_to_equity() -> None:
    assert debt_to_equity(SAMPLE) == pytest.approx(800.0 / 1200.0)


def test_return_on_equity() -> None:
    assert return_on_equity(SAMPLE) == pytest.approx(100.0 / 1200.0)


def test_return_on_assets() -> None:
    assert return_on_assets(SAMPLE) == pytest.approx(100.0 / 2000.0)


def test_net_margin() -> None:
    assert net_margin(SAMPLE) == pytest.approx(0.10)


def test_calculate_all_ratios() -> None:
    ratios = calculate_all_ratios(SAMPLE)

    assert set(ratios) == {
        "current_ratio",
        "debt_to_equity",
        "return_on_equity",
        "return_on_assets",
        "net_margin",
    }
    assert ratios["current_ratio"] == pytest.approx(2.0)
