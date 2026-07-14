"""Small pandas-based analysis helpers used during the data analysis weeks."""

from __future__ import annotations

import pandas as pd


def add_daily_returns(prices: pd.DataFrame, price_column: str = "close") -> pd.DataFrame:
    """Add a simple daily return column to a prices DataFrame.

    Args:
        prices: A DataFrame containing at least price_column.
        price_column: The column to compute returns from.

    Returns:
        A copy of prices with a new "return" column. The first row's
        return is NaN, since there is no prior price to compare against.
    """
    result = prices.copy()
    result["return"] = result[price_column].pct_change()
    return result


def rolling_average(series: pd.Series, window: int) -> pd.Series:
    """Calculate a rolling average over the given window.

    Args:
        series: A numeric series, such as a column of daily returns.
        window: Number of periods in each rolling window.

    Returns:
        A series the same length as the input. The first (window - 1)
        values are NaN, since a full window isn't available yet.
    """
    return series.rolling(window=window).mean()


def rolling_volatility(series: pd.Series, window: int) -> pd.Series:
    """Calculate rolling volatility (standard deviation) over the given window.

    Args:
        series: A numeric series, such as a column of daily returns.
        window: Number of periods in each rolling window.

    Returns:
        A series the same length as the input, with the same leading
        NaNs as rolling_average for the same reason.
    """
    return series.rolling(window=window).std()


def cumulative_growth(returns: pd.Series) -> pd.Series:
    """Calculate cumulative growth of $1 invested, given a series of returns.

    Args:
        returns: A series of decimal returns (e.g. 0.05 for 5%). Any
            leading NaN (from add_daily_returns' first row) is treated
            as a 0% return for that period.

    Returns:
        A series where each value is the cumulative growth factor —
        1.05 means a 5% cumulative gain since the start of the series.
    """
    return (1 + returns.fillna(0)).cumprod()
