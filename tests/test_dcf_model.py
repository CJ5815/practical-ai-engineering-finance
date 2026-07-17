import formulas
import pytest

from ai_finance_course.skills.dcf_model import (
    DCFAssumptions,
    build_dcf_workbook,
    discount_factors,
    intrinsic_value_per_share,
    margin_of_safety_pct,
    project_revenue,
    terminal_value,
    unlevered_fcf,
)

ASSUMPTIONS = DCFAssumptions(
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


def test_project_revenue() -> None:
    revenues = project_revenue(1000.0, [0.10, 0.10])

    assert revenues == pytest.approx([1100.0, 1210.0])


def test_unlevered_fcf() -> None:
    fcfs = unlevered_fcf([1100.0, 1210.0], 0.20, 0.25, 0.05, 0.06, 0.01)

    assert fcfs == pytest.approx([143.0, 157.3])


def test_discount_factors() -> None:
    factors = discount_factors(0.10, 2)

    assert factors == pytest.approx([0.9090909090909091, 0.8264462809917354])


def test_terminal_value() -> None:
    tv = terminal_value(157.3, 0.10, 0.03)

    assert tv == pytest.approx(2314.557142857143)


def test_intrinsic_value_per_share() -> None:
    ivps = intrinsic_value_per_share(ASSUMPTIONS)

    assert ivps == pytest.approx(19.728571428571428)


def test_margin_of_safety_pct_undervalued() -> None:
    # Intrinsic value above current price: positive margin of safety.
    assert margin_of_safety_pct(intrinsic_value=20.0, current_price=15.0) == pytest.approx(0.25)


def test_margin_of_safety_pct_overvalued() -> None:
    # Intrinsic value below current price: negative margin of safety.
    assert margin_of_safety_pct(intrinsic_value=20.0, current_price=25.0) == pytest.approx(-0.25)


def test_dcf_workbook_formulas_match_python(tmp_path) -> None:
    """The generated .xlsx isn't just structurally correct — its formulas
    actually recalculate to the same numbers the pure Python functions
    produce. This loads the real workbook into a formula engine and
    recalculates it, rather than only checking labels/cells exist.
    """
    path = tmp_path / "dcf.xlsx"
    build_dcf_workbook(ASSUMPTIONS, str(path))

    xl_model = formulas.ExcelModel().loads(str(path)).finish()
    solution = xl_model.calculate()

    sheet_key = f"'[{path.name}]DCF MODEL'!"
    recalculated_ivps = solution[f"{sheet_key}B19"].value[0, 0]
    recalculated_margin = solution[f"{sheet_key}B21"].value[0, 0]

    assert recalculated_ivps == pytest.approx(intrinsic_value_per_share(ASSUMPTIONS))
    assert recalculated_margin == pytest.approx(
        margin_of_safety_pct(intrinsic_value_per_share(ASSUMPTIONS), ASSUMPTIONS.current_share_price)
    )
