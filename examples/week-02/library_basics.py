"""Week 2: a first look at numpy, pandas, polars, matplotlib, and statsmodels.

Run this file directly:

    python examples/week-02/library_basics.py

Each section below is independent — read them top to bottom.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl
import statsmodels.api as sm
from matplotlib import pyplot as plt

DATA_PATH = "data/sample/prices.csv"


def numpy_basics() -> None:
    """NumPy: fast, vectorized math over arrays of numbers."""
    print("\n--- NumPy ---")

    prices = np.array([100.0, 101.25, 100.80, 103.10, 104.00])

    # Vectorized: this computes all four daily returns in one step,
    # instead of writing a loop that does the division one price at a time.
    daily_returns = (prices[1:] / prices[:-1]) - 1

    print("Daily returns:", daily_returns)
    print("Average return:", daily_returns.mean())
    print("Volatility (std dev):", daily_returns.std())


def pandas_basics() -> None:
    """pandas: label-aware tables (DataFrames). Week 3 goes much deeper."""
    print("\n--- pandas ---")

    prices = pd.read_csv(DATA_PATH)

    # pct_change() computes the same simple return as numpy above,
    # but pandas keeps track of the date/ticker labels for each row.
    prices["return"] = prices["close"].pct_change()

    print(prices.head())


def polars_basics() -> None:
    """polars: a newer, faster DataFrame library with a different API."""
    print("\n--- polars ---")

    prices = pl.read_csv(DATA_PATH)

    # with_columns adds a column without changing the others.
    # shift(1) looks at the previous row, same idea as pandas' pct_change.
    prices = prices.with_columns(
        (pl.col("close") / pl.col("close").shift(1) - 1).alias("return")
    )

    print(prices.head())


def matplotlib_basics() -> None:
    """matplotlib: the standard plotting library."""
    print("\n--- matplotlib ---")

    prices = pd.read_csv(DATA_PATH)

    plt.plot(prices["date"], prices["close"])
    plt.title("DEMO Closing Price")
    plt.xlabel("Date")
    plt.ylabel("Price ($)")
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Opens a window on your Mac. In a notebook, the chart renders inline
    # instead — no plt.show() needed there.
    plt.show()


def statsmodels_basics() -> None:
    """statsmodels: statistical models, such as linear regression."""
    print("\n--- statsmodels ---")

    # Toy data: a stock that tends to move 1.2x the market, plus some noise.
    # This is the same idea as a stock's "beta" in equity research.
    rng = np.random.default_rng(seed=42)
    market_return = rng.normal(0, 0.01, size=50)
    stock_return = 1.2 * market_return + rng.normal(0, 0.005, size=50)

    # statsmodels requires an explicit intercept column; add_constant does that.
    predictors = sm.add_constant(market_return)
    model = sm.OLS(stock_return, predictors).fit()

    intercept, slope = model.params
    print(f"Estimated intercept: {intercept:.4f}")
    print(f"Estimated slope (beta): {slope:.4f}")  # should land near 1.2


def main() -> None:
    numpy_basics()
    pandas_basics()
    polars_basics()
    statsmodels_basics()
    matplotlib_basics()  # last, since it opens a window


if __name__ == "__main__":
    main()
