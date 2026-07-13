import pytest

from ai_finance_course.returns import simple_return


def test_positive_return() -> None:
    assert simple_return(100.0, 105.0) == pytest.approx(0.05)


def test_negative_return() -> None:
    assert simple_return(100.0, 90.0) == pytest.approx(-0.10)


def test_zero_beginning_price_is_invalid() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        simple_return(0.0, 100.0)
