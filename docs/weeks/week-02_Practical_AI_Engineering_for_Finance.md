# Week 2: Python Fundamentals for Finance

**Course:** Practical AI Engineering for Finance  
**Audience:** Senior undergraduate students  
**Schedule:** 1 hour per day, 4 days per week  
**Week Theme:** Variables, collections, conditionals, loops, functions, comments, modules, and a first look at Python's data and finance libraries

---

## Week Overview

Week 1 got your machine ready — Python, Git, VS Code, and a first program. Week 2 is where you start writing real Python: the building blocks (variables, strings, numbers, lists, dictionaries), control flow (conditionals, loops), and the two habits that separate working code from good code — functions with type hints, and comments that explain *why*, not *what*.

By the end of the week you'll turn a return calculation you write "by hand" on Day 2 into a tested, reusable function by Day 4 — the same pattern (rough version first, tested function later) you'll repeat all semester on the equity research capstone. You'll also get a first look at the libraries — numpy, pandas, polars, matplotlib, and statsmodels — that Weeks 3 and beyond build on.

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: Variables, Strings, Numbers, Lists, and Dictionaries](#day-1-variables-strings-numbers-lists-and-dictionaries)
- [Day 2: Conditionals and Loops](#day-2-conditionals-and-loops)
- [Day 3: Functions, Comments, and Modules](#day-3-functions-comments-and-modules)
- [Day 4: Testing and Communication](#day-4-testing-and-communication)
- [Python's Data and Finance Libraries: A First Look](#pythons-data-and-finance-libraries-a-first-look)
- [Week 2 Coding Lab](#week-2-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 2 Quiz](#week-2-quiz)
- [Week 2 Project Submission Checklist](#week-2-project-submission-checklist)
- [Week 2 Reflection](#week-2-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Next Week](#next-week)

---

# Learning Objectives

By the end of Week 2, you should be able to:

- Use variables, strings, numbers, lists, and dictionaries to represent financial data.
- Write conditionals and loops to make decisions and repeat work.
- Write functions with type hints and clear docstrings.
- Explain what makes a comment useful versus redundant, and apply that consistently.
- Organize code into modules and import from your own files.
- Recognize numpy, pandas, polars, matplotlib, and statsmodels, and know what each is for.
- Explain the difference between running code as a script and running it as a notebook, and when to use each.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | Variables, strings, numbers, lists, and dictionaries | A company dictionary program |
| Day 2 | Conditionals and loops | Hand-written return classification |
| Day 3 | Functions, comments, and modules | A `classify_return()` function |
| Day 4 | Testing and communication | Tested return-classification functions |

Each class is designed for approximately one hour, using the same session structure as Week 1: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: Variables, Strings, Numbers, Lists, and Dictionaries

## 1.1 Variables and Data Types

A variable is a name that points to a value. Python figures out the type automatically from the value you assign — you don't declare it yourself.

```python
ticker = "DEMO"         # str: text
price = 104.00           # float: a number with a decimal point
shares = 10               # int: a whole number
on_watchlist = True       # bool: True or False

print(type(ticker), type(price), type(shares), type(on_watchlist))
```

`str`, `int`, `float`, and `bool` are the four types you'll use constantly in finance code.

## 1.2 Strings

```python
ticker = "demo"

print(ticker.upper())    # "DEMO"
print(ticker.strip())    # removes leading/trailing whitespace

# f-strings embed expressions directly inside text (you used these in Week 1)
print(f"Ticker: {ticker.upper()}, Price: ${104.00:.2f}")
```

## 1.3 Numbers and Arithmetic

```python
beginning_price = 100.0
ending_price = 105.0

change = ending_price - beginning_price     # 5.0
percent_change = change / beginning_price   # 0.05

print(round(percent_change, 4))
```

Watch for division: in Python 3, `/` always returns a `float` (`5 / 2` is `2.5`); `//` performs floor division and drops the remainder (`5 // 2` is `2`).

## 1.4 Lists

A list holds an ordered sequence of values — well suited to a time series of prices.

```python
closing_prices = [100.00, 101.25, 100.80, 103.10, 104.00]

print(closing_prices[0])       # first price: 100.00
print(closing_prices[-1])      # most recent price: 104.00
print(len(closing_prices))     # how many prices: 5

closing_prices.append(105.50)  # add today's close to the end
```

## 1.5 Dictionaries

A dictionary maps keys to values — useful when position doesn't carry meaning but the field name does.

```python
company = {
    "ticker": "DEMO",
    "sector": "Technology",
    "price": 104.00,
}

print(company["ticker"])     # look up a value by key
company["price"] = 105.50    # update an existing value
company["pe_ratio"] = 22.4   # add a new key

for key, value in company.items():
    print(f"{key}: {value}")
```

## Day 1 Activity

Create a dictionary describing a company you're interested in, with at least four fields (`ticker`, `sector`, `price`, and one more of your choice). Print each field using an f-string.

---

# Day 2: Conditionals and Loops

## 2.1 Conditionals

```python
price_change = -2.35

if price_change > 0:
    print("Price increased")
elif price_change < 0:
    print("Price decreased")
else:
    print("Price unchanged")
```

`elif` lets you check additional conditions in sequence, instead of nesting `if` statements inside each other.

## 2.2 Loops

```python
closing_prices = [100.00, 101.25, 100.80, 103.10, 104.00]

# for loop: runs once per item — use this whenever you already have a collection
for price in closing_prices:
    print(f"${price:.2f}")

# while loop: runs until a condition becomes false — use this when the
# stopping point isn't a fixed collection you can loop over directly
day = 0
while day < len(closing_prices):
    print(closing_prices[day])
    day += 1
```

Prefer `for` whenever you're iterating over a known collection; reach for `while` only when you don't have one to loop over.

## 2.3 Classifying a Return by Hand

```python
beginning_price = 100.0
ending_price = 97.50

return_value = (ending_price / beginning_price) - 1

if return_value > 0:
    classification = "positive"
elif return_value < 0:
    classification = "negative"
else:
    classification = "flat"

print(f"Return: {return_value:.2%} ({classification})")
```

This is exactly the logic you'll turn into a reusable `classify_return()` function on Day 3. Hard-coding the numbers is fine for now — Day 3 is about not repeating this block every time you need it.

## Day 2 Activity

Using the loop pattern from §2.2, print the classification for at least five different `closing_prices` values you choose yourself, including at least one flat (zero) return.

---

# Day 3: Functions, Comments, and Modules

## 3.1 Functions and Type Hints

```python
def simple_return(beginning_price: float, ending_price: float) -> float:
    """Calculate a simple asset return.

    Args:
        beginning_price: Price at the beginning of the period. Must be positive.
        ending_price: Price at the end of the period. Must be non-negative.

    Returns:
        The decimal return. For example, 0.05 represents 5%.
    """
    return (ending_price / beginning_price) - 1
```

This is the actual `simple_return` function from `src/ai_finance_course/returns.py` — the same one Week 1's sample notebook imported. Type hints (`: float`, `-> float`) don't change how the code runs; they tell you, your teammates, and your editor what each argument and return value should be. Because Pylance (installed in Week 1) reads these hints, it will flag a call like `simple_return("100", 105)` as wrong before you ever run the program.

## 3.2 Writing Good Comments

A comment should tell the reader something the code itself can't — the *why*, not the *what*. If removing a comment wouldn't confuse anyone, it's not adding value.

```python
# Bad: restates what the code already says
percent_change = change / beginning_price  # divide change by beginning_price

# Good: explains a non-obvious reason
# Use simple (not log) returns here — matches how the finance team
# reports performance in the monthly deck.
percent_change = change / beginning_price
```

A few rules of thumb:

- **Docstrings for functions.** Every function gets a short docstring: what it does, its `Args`, its `Returns`, and any `Raises` — see `simple_return` above.
- **Inline comments for surprises.** Use them for business rules, workarounds, or anything a future reader would otherwise have to guess at.
- **Don't narrate obvious code.** `i += 1  # add one to i` teaches the reader nothing.
- **A wrong comment is worse than no comment.** If you change the code, update or delete the comment in the same edit — a stale comment actively misleads the next reader.

Every code example for the rest of this course follows these rules — you'll see the pattern repeated rather than restated.

## 3.3 Organizing Code into Modules

Any `.py` file is a **module** — you can import functions from one file into another, instead of copy-pasting code.

```python
# File: src/ai_finance_course/returns.py
def simple_return(beginning_price: float, ending_price: float) -> float:
    ...
```

```python
# File: anywhere else in the project
from ai_finance_course.returns import simple_return

result = simple_return(100.0, 105.0)
```

This is different from the third-party *modules* (libraries) covered next — `import pandas` works the same way, except pandas' code lives in a package you installed instead of a file you wrote.

## Day 3 Activity

Add a docstring (following §3.2's rules) to any function you wrote on Day 1 or Day 2 that doesn't have one yet.

---

# Day 4: Testing and Communication

## 4.1 Manual Testing vs. Automated Testing

Manually testing `simple_return` means running it once, eyeballing the printed result, and trusting yourself to remember to check it again after every change. Automated tests do that checking for you, every time:

```python
# File: tests/test_returns.py
import pytest

from ai_finance_course.returns import simple_return


def test_positive_return() -> None:
    assert simple_return(100.0, 105.0) == pytest.approx(0.05)
```

Run the whole suite with:

```bash
pytest
```

If `simple_return` ever breaks — for anyone, for any reason — this test fails immediately instead of silently producing a wrong number in a report.

## 4.2 Building and Testing `classify_return`

Turn Day 2's hand-written if/elif/else (§2.3) into a real function:

```python
def classify_return(value: float) -> str:
    """Classify a return as positive, negative, or flat.

    Args:
        value: A decimal return, such as the output of simple_return.

    Returns:
        "positive" if value > 0, "negative" if value < 0, otherwise "flat".
    """
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "flat"
```

And a matching test, following §4.1's pattern:

```python
def test_classify_flat_return() -> None:
    assert classify_return(0.0) == "flat"
```

`classify_return` and its tests already exist in `src/ai_finance_course/returns.py` and `tests/test_returns.py` — read them there, then write one more test case of your own (for example, a negative return).

## Day 4 Activity

Write a short reflection: what did you build, what failed, how did you fix it, and how would you explain `classify_return` in an interview?

---

# Python's Data and Finance Libraries: A First Look

## Why These Libraries?

Plain Python lists and dictionaries work, but they get slow and awkward once you're working with thousands of prices across hundreds of companies. The libraries below are what the rest of this course — and most real finance software — builds on instead. This section is a first look, not a deep dive: Week 3 covers pandas in depth once you've had a chance to meet it here first.

Every example below also exists as runnable code in `examples/week-02/library_basics.py` (and an identical `library_basics.ipynb` notebook) — see [Running as a Script vs. a Notebook](#running-as-a-script-vs-a-notebook) below.

## NumPy — Fast Numeric Arrays

NumPy arrays support vectorized math: one operation applies to every element at once, instead of writing a loop.

```python
import numpy as np

prices = np.array([100.0, 101.25, 100.80, 103.10, 104.00])

# Vectorized: computes all four daily returns in one step
daily_returns = (prices[1:] / prices[:-1]) - 1

print(daily_returns.mean())  # average daily return
print(daily_returns.std())   # volatility (standard deviation)
```

## pandas — Tables of Data

A pandas DataFrame is a table that keeps track of row and column labels — Week 3 goes much deeper into it.

```python
import pandas as pd

prices = pd.read_csv("data/sample/prices.csv")

# pct_change() computes the same return as the numpy example above,
# but pandas keeps the date/ticker labels attached to each row.
prices["return"] = prices["close"].pct_change()

print(prices.head())
```

## polars — A Faster DataFrame Alternative

polars solves the same table problem as pandas, with a different API and better performance on large files. Think of it as an alternative worth knowing about, not a second course to learn right now.

```python
import polars as pl

prices = pl.read_csv("data/sample/prices.csv")

# with_columns adds a column; shift(1) looks at the previous row,
# the same idea as pandas' pct_change.
prices = prices.with_columns(
    (pl.col("close") / pl.col("close").shift(1) - 1).alias("return")
)

print(prices.head())
```

## Matplotlib — Basic Plotting

```python
import pandas as pd
from matplotlib import pyplot as plt

prices = pd.read_csv("data/sample/prices.csv")

plt.plot(prices["date"], prices["close"])
plt.title("DEMO Closing Price")
plt.xlabel("Date")
plt.ylabel("Price ($)")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()  # opens a window when run as a script; renders inline in a notebook
```

## statsmodels — Basic Statistics

statsmodels fits statistical models — here, a linear regression estimating a stock's "beta" against the market, the same concept used in equity research.

```python
import numpy as np
import statsmodels.api as sm

# Toy data: a stock that tends to move 1.2x the market, plus some noise
rng = np.random.default_rng(seed=42)
market_return = rng.normal(0, 0.01, size=50)
stock_return = 1.2 * market_return + rng.normal(0, 0.005, size=50)

predictors = sm.add_constant(market_return)  # adds the intercept term
model = sm.OLS(stock_return, predictors).fit()

print(model.params)  # [intercept, slope] — slope should land near 1.2
```

## Running as a Script vs. a Notebook

`examples/week-02/library_basics.py` and `examples/week-02/library_basics.ipynb` contain the same logic. Run the script with:

```bash
python examples/week-02/library_basics.py
```

Or open the notebook in VS Code, select the `.venv` interpreter as the kernel (§2.10 in Week 1), and run each cell with `Shift+Enter`.

| | Script (`.py`) | Notebook (`.ipynb`) |
|---|---|---|
| Execution | Top to bottom, same order every time | Cell by cell, in whatever order you run them |
| Output | Printed to the terminal (or a saved file) | Shown inline below each cell, including charts |
| Version control | Clean text diffs | Diffs include embedded output — harder to review |
| Best for | Reusable, tested, automatable logic | Exploring data and prototyping |

Use a notebook while you're still figuring out what the data looks like or what a chart should show. Once the logic is settled and you want to reuse, test, or automate it — like `simple_return` and `classify_return` — move it into a module, the way Day 3 and Day 4 did.

---

# Week 2 Coding Lab

## Student Return Classifier

Extend `src/ai_finance_course/returns.py`:

- add `classify_return()` (§4.2), if you haven't already;
- write at least one additional test in `tests/test_returns.py` beyond the ones already there;
- run `pytest` and confirm every test passes.

### Required Features

- type hints on every function;
- a docstring on every function, following §3.2;
- at least one test per function;
- no runtime errors;
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: Company Dictionary

Build the dictionary from the [Day 1 Activity](#day-1-activity) into a small program that prints a formatted summary.

## Exercise 2: Loop Practice

Write a loop that prints only the *negative* returns from a list of returns you define yourself.

## Exercise 3: A Second Classifier

Write a function `classify_volatility(std_dev: float) -> str` that returns `"low"`, `"medium"`, or `"high"` based on thresholds you choose. Add a docstring and at least one test.

## Exercise 4: Library Exploration

Open `examples/week-02/library_basics.ipynb`, change the sample prices in the numpy or pandas cell, and re-run it. Confirm the printed statistics change accordingly.

## Exercise 5: Git Practice

Make three commits: one for `classify_return`, one for its tests, and one for your Exercise 3 classifier.

---

# Common Mistakes

## Comparing floats with `==`

Floating-point math can produce tiny rounding errors. Prefer `pytest.approx()` in tests (as `test_returns.py` already does) instead of exact equality.

## Forgetting `elif`

```python
# Wrong: both branches can run, since these are two separate if statements
if return_value > 0:
    classification = "positive"
if return_value < 0:
    classification = "negative"
```

Use `elif`/`else` when only one branch should execute.

## Off-by-one errors in loops

```python
# Wrong: raises IndexError on the last iteration
for i in range(len(closing_prices)):
    print(closing_prices[i + 1])
```

Iterate over the list directly (`for price in closing_prices`) unless you specifically need the index.

## Comments that restate the code

Revisit §3.2 if a comment just repeats what the line already says in English.

---

# Interview Preparation

1. What's the difference between a list and a dictionary, and when would you use each?
2. What does `elif` do that two separate `if` statements don't?
3. What's the difference between a `for` loop and a `while` loop?
4. Why use type hints if Python doesn't enforce them at runtime?
5. What makes a comment useful versus redundant?
6. What's the difference between a module you wrote and a third-party library?
7. Why write automated tests instead of just running the code and checking the output?
8. What's the difference between pandas and polars?
9. When would you choose a Jupyter notebook over a plain Python script, and vice versa?
10. What does a linear regression's slope represent in the statsmodels "beta" example?

---

# Week 2 Quiz

## Multiple Choice

1. Which type would Python assign to `shares = 10`?

   A. `str`  
   B. `float`  
   C. `int`  
   D. `bool`

2. What does `closing_prices[-1]` return?

   A. The first item  
   B. The last item  
   C. An error  
   D. The list's length

3. Which loop should you use to iterate over a list you already have?

   A. `while`  
   B. `for`  
   C. `if`  
   D. `def`

4. What is the purpose of a type hint like `-> float`?

   A. It converts the return value to a float at runtime  
   B. It documents the expected return type for readers and tools like Pylance  
   C. It makes the function run faster  
   D. It is required by Python to run the function

5. Which library is best described as "a faster alternative to pandas with a different API"?

   A. numpy  
   B. matplotlib  
   C. polars  
   D. statsmodels

## Short Answer

6. Explain the difference between a script and a notebook in your own words.

7. Why should a comment explain "why" instead of "what"?

8. What is the purpose of an automated test, compared to running code manually?

9. What does `classify_return` do, and why is it useful to have as a function instead of inline code?

10. Name one thing numpy, pandas, and polars all have in common, and one way they differ.

---

# Week 2 Project Submission Checklist

- [ ] `classify_return()` exists in `src/ai_finance_course/returns.py` with a docstring and type hints.
- [ ] At least one new test exists in `tests/test_returns.py` beyond what was already there.
- [ ] `pytest` passes with no failures.
- [ ] Comments follow §3.2 — no restated-code comments.
- [ ] `examples/week-02/library_basics.py` runs without errors.
- [ ] `examples/week-02/library_basics.ipynb` runs without errors, cell by cell.
- [ ] All work is committed and pushed to GitHub.

---

# Week 2 Reflection

Write 200–300 words answering:

1. What did you build this week?
2. Which was clearer to you: the script or the notebook version of the library examples? Why?
3. What error did you encounter, and how did you fix it?
4. What's one comment you wrote (or deleted) after learning §3.2's rules?
5. What would you improve?

Save as:

```text
week2_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Variable | A name that points to a value |
| List | An ordered, mutable collection of values |
| Dictionary | A collection of key-value pairs |
| Conditional | Code that runs only when a condition is true |
| Loop | Code that repeats over a collection or until a condition changes |
| Function | A named, reusable block of code |
| Type hint | An annotation documenting a value's expected type |
| Docstring | A structured comment describing what a function does |
| Module | A `.py` file whose code can be imported elsewhere |
| Automated test | Code that checks other code's behavior automatically |
| NumPy | A library for fast, vectorized numeric arrays |
| pandas | A library for labeled data tables (DataFrames) |
| polars | A faster DataFrame library with a different API than pandas |
| Matplotlib | Python's standard plotting library |
| statsmodels | A library for statistical models such as linear regression |
| Script | A `.py` file that runs top to bottom in one pass |
| Notebook | A `.ipynb` file of cells run individually, with inline output |

---

# Week Summary

During Week 2, you:

- used variables, strings, numbers, lists, and dictionaries to represent financial data;
- wrote conditionals and loops, including a hand-written return classifier;
- wrote functions with type hints and docstrings;
- learned rules for writing comments that explain *why*, not *what*;
- organized code into modules and imported your own functions;
- wrote and ran automated tests with pytest;
- built and tested `classify_return()`;
- got a first look at numpy, pandas, polars, matplotlib, and statsmodels;
- ran the same code as both a `.py` script and a `.ipynb` notebook, and discussed when to use each.

---

# Suggested Reading

## Required

- Python Tutorial, Data Structures chapter (lists, dicts)
- Real Python, "Python Type Checking"
- pytest documentation, Getting Started

## Recommended

- Eric Matthes, *Python Crash Course*
- Wes McKinney, *Python for Data Analysis*
- NumPy, pandas, polars, matplotlib, and statsmodels official "Getting Started" guides

---

# Next Week

## Week 3: Python Data Analysis

Week 3 goes deep on pandas — the library you only met briefly this week:

- DataFrames and CSV files;
- filtering, sorting, and missing values;
- group-by and rolling calculations;
- building a performance summary from sample prices.

You'll use these skills to calculate returns, rolling averages, volatility, and cumulative growth — the analysis layer of the capstone.
