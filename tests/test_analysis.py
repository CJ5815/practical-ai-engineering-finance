import pandas as pd
import pytest

from ai_finance_course.analysis import (
    add_daily_returns,
    cumulative_growth,
    rolling_average,
    rolling_volatility,
)


def test_add_daily_returns() -> None:
    prices = pd.DataFrame({"close": [100.0, 110.0, 99.0]})

    result = add_daily_returns(prices)

    assert result["return"].iloc[0] != result["return"].iloc[0]  # NaN != NaN
    assert result["return"].iloc[1] == pytest.approx(0.10)
    assert result["return"].iloc[2] == pytest.approx(-0.10)


def test_add_daily_returns_does_not_mutate_input() -> None:
    prices = pd.DataFrame({"close": [100.0, 110.0]})

    add_daily_returns(prices)

    assert "return" not in prices.columns


def test_rolling_average() -> None:
    series = pd.Series([1.0, 2.0, 3.0, 4.0])

    result = rolling_average(series, window=2)

    assert result.iloc[1] == pytest.approx(1.5)
    assert result.iloc[3] == pytest.approx(3.5)


def test_rolling_volatility() -> None:
    series = pd.Series([1.0, 1.0, 1.0, 1.0])

    result = rolling_volatility(series, window=2)

    assert result.iloc[1] == pytest.approx(0.0)


def test_cumulative_growth() -> None:
    returns = pd.Series([0.10, 0.10])

    result = cumulative_growth(returns)

    assert result.iloc[0] == pytest.approx(1.10)
    assert result.iloc[1] == pytest.approx(1.21)
