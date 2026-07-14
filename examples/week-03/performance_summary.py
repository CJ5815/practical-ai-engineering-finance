"""Week 3: build a performance summary from sample prices.

Run this file directly:

    python examples/week-03/performance_summary.py
"""

from __future__ import annotations

import pandas as pd
from matplotlib import pyplot as plt

from ai_finance_course.analysis import (
    add_daily_returns,
    cumulative_growth,
    rolling_average,
    rolling_volatility,
)

DATA_PATH = "data/sample/prices.csv"
ROLLING_WINDOW = 3  # short window since the sample data only has 5 rows


def main() -> None:
    prices = pd.read_csv(DATA_PATH)

    # Reusable, tested functions from ai_finance_course.analysis —
    # this script just wires them together and reports the result.
    prices = add_daily_returns(prices)
    prices["rolling_avg_return"] = rolling_average(prices["return"], ROLLING_WINDOW)
    prices["rolling_volatility"] = rolling_volatility(prices["return"], ROLLING_WINDOW)
    prices["cumulative_growth"] = cumulative_growth(prices["return"])

    print(prices)

    plt.plot(prices["date"], prices["cumulative_growth"])
    plt.title("DEMO Cumulative Growth of $1")
    plt.xlabel("Date")
    plt.ylabel("Growth Factor")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()  # opens a window when run as a script; renders inline in a notebook


if __name__ == "__main__":
    main()
