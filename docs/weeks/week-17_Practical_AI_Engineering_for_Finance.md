# Week 17: Investment Philosophy Skills

**Course:** Practical AI Engineering for Finance  
**Audience:** Senior undergraduate students  
**Schedule:** 1 hour per day, 6 days (this week only — an optional, advanced extension)  
**Week Theme:** Building a reusable "skill" that evaluates a stock under a specific investment philosophy — thesis, catalysts, ratio analysis, and a real multi-year DCF model in Excel

---

## Week Overview

Week 16 closed out the core, 16-week capstone. Week 17 is an optional extension: building the first of what could eventually be several **skills** — pluggable modules, each implementing one investment philosophy's process for evaluating a stock. This week builds **Value Investing** (Graham/Buffett-style: intrinsic value, margin of safety, financial strength) — a second philosophy later (growth, dividend, etc.) means writing a new prompt and evaluation function, not new infrastructure.

This week assumes you already know the basics of DCF and financial-statement modeling — it's about the *engineering*: how do you build a financial model reproducibly in Python, hand a real Excel workbook to a user, validate an LLM's output before trusting it, and test all of it without a real API key or a spreadsheet engine in CI.

Because it adds a genuinely new deliverable — a real, formula-driven Excel DCF model — this week runs six sessions instead of four.

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: Investment Thesis and Evidence-Based Prompting](#day-1-investment-thesis-and-evidence-based-prompting)
- [Day 2: Financial Statement Model and Ratio Analysis](#day-2-financial-statement-model-and-ratio-analysis)
- [Day 3: Building the DCF Model in Excel with Python](#day-3-building-the-dcf-model-in-excel-with-python)
- [Day 4: Catalysts, Bull/Bear Case, and Mapping the Timeline](#day-4-catalysts-bullbear-case-and-mapping-the-timeline)
- [Day 5: Testing the Model](#day-5-testing-the-model)
- [Day 6: Wiring the Claude Skill Wrapper and Wrap-Up](#day-6-wiring-the-claude-skill-wrapper-and-wrap-up)
- [Week 17 Coding Lab](#week-17-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 17 Quiz](#week-17-quiz)
- [Week 17 Project Submission Checklist](#week-17-project-submission-checklist)
- [Week 17 Reflection](#week-17-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Where to Go From Here](#where-to-go-from-here)

---

# Learning Objectives

By the end of Week 17, you should be able to:

- Explain what a "skill" is in this context, and design one so a second philosophy can reuse the same infrastructure.
- Build an evidence-based LLM prompt and validate its structured JSON response.
- Build a typed financial statement snapshot and calculate standard ratios from it.
- Build a multi-year DCF model as pure, testable Python functions.
- Generate a real, formula-driven Excel workbook from those functions with `openpyxl`.
- Verify the workbook's formulas actually compute correctly, not just that they exist.
- Render a bull/bear catalyst timeline with matplotlib.
- Wrap a tested Python module in a thin Claude Skill.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | Investment thesis & evidence-based prompting | Skill architecture, prompt template |
| Day 2 | Financial statement model & ratio analysis | `FinancialStatements`, ratio functions |
| Day 3 | Building the DCF model in Excel with Python | A real, formula-driven `.xlsx` |
| Day 4 | Catalysts, bull/bear case, and the timeline | Catalyst timeline chart |
| Day 5 | Testing the model | Pure-function + Excel-recalculation tests |
| Day 6 | Claude Skill wrapper & wrap-up | `SKILL.md`, end-to-end run |

Each session follows the same structure as prior weeks: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: Investment Thesis and Evidence-Based Prompting

## 1.1 What Is a "Skill"?

A **skill**, in this course's sense, is a self-contained module implementing one investment philosophy's process for evaluating a company: it takes evidence and financial data in, and produces a structured thesis out. The point of designing it this way is that a second philosophy — growth investing, dividend investing — can be added later by writing a new prompt and a new evaluation function, without touching the shared types, the ratio math, or the DCF model.

This skill is deliberately decoupled from any specific retrieval system: it takes a list of already-retrieved evidence chunks as a plain argument, the same way `edgar.py`'s functions (Week 4) take an already-configured `httpx.Client` rather than owning HTTP setup themselves. If you built a RAG pipeline in Weeks 9–11, its output is exactly what feeds this skill.

## 1.2 Shared Types

```python
# File: src/ai_finance_course/skills/base.py
class EvidenceChunk(BaseModel):
    text: str
    source: str


class FinancialStatements(BaseModel):
    revenue: float
    net_income: float
    total_assets: float
    total_liabilities: float
    total_equity: float
    current_assets: float
    current_liabilities: float


class Catalyst(BaseModel):
    description: str
    timeframe: str
    direction: Literal["bull", "bear"]


class InvestmentThesis(BaseModel):
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
```

Every philosophy produces the same `InvestmentThesis` shape — that consistency is what makes "multiple skills" a realistic goal rather than a slogan.

## 1.3 The `InvestmentPhilosophy` Protocol

```python
class InvestmentPhilosophy(Protocol):
    def evaluate(
        self, ticker: str, evidence: list[EvidenceChunk], financials: FinancialStatements
    ) -> InvestmentThesis: ...
```

A `Protocol` (not an abstract base class) means any object with a matching `evaluate` method satisfies it — no inheritance required. This week implements one concrete version of that shape as a function, `value_investor.evaluate_company`, rather than a class; a `Protocol` still documents the contract future philosophies should follow.

## 1.4 Writing the Evidence-Based Prompt

Following Week 6's role/task/evidence/constraints/output-format structure:

```python
def build_prompt(ticker, evidence, ratios, intrinsic_value, current_price, margin_of_safety) -> str:
    evidence_block = "\n".join(f"[{i + 1}] ({e.source}): {e.text}" for i, e in enumerate(evidence))
    ratios_block = "\n".join(f"- {name}: {value:.4f}" for name, value in ratios.items())

    return f"""ROLE: You are a value investor in the tradition of Benjamin Graham and \
Warren Buffett...

TASK: Evaluate {ticker} and produce an investment thesis based only on the evidence \
and numbers below.

EVIDENCE:
{evidence_block}

FINANCIAL RATIOS:
{ratios_block}

VALUATION:
- Intrinsic value per share (DCF): {intrinsic_value:.2f}
...

CONSTRAINTS:
- Base every claim only on the evidence and numbers above. Do not invent facts.
- List catalysts in chronological order, nearest-term first.

OUTPUT FORMAT: Return ONLY valid JSON, no other text, matching this shape: ..."""
```

Two details worth noticing: the constraints explicitly forbid inventing facts (an LLM will confidently fabricate detail if not told not to), and the output format asks for JSON *only* — read [`src/ai_finance_course/skills/value_investor.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/ai_finance_course/skills/value_investor.py) for the full prompt.

## 1.5 Injecting the LLM Call

`evaluate_company` never imports an LLM SDK or calls the network itself — it takes `generate: Callable[[str], str]` as a parameter, exactly the dependency-injection pattern Weeks 4–5 used for `httpx.Client`:

```python
def evaluate_company(ticker, evidence, financials, dcf_assumptions, generate) -> InvestmentThesis:
    ...
    raw_response = generate(prompt)
    parsed = json.loads(_extract_json(raw_response))
    return InvestmentThesis(...)
```

Tests pass a stub `generate` returning canned JSON (Day 5). The real example script's `generate` posts to Anthropic's Messages API directly via `httpx` — no new SDK dependency, reusing what Weeks 4–5 already taught.

## Day 1 Activity

Write a one-paragraph explanation, in your own words, of why `evaluate_company` takes `generate` as a parameter instead of calling an LLM API directly inside the function.

---

# Day 2: Financial Statement Model and Ratio Analysis

## 2.1 The `FinancialStatements` Model

`FinancialStatements` (§1.2) is the "model of financial statements" this week's required output asks for: a structured, typed snapshot — not a multi-year projection by itself. The projection comes Day 3.

## 2.2 Liquidity, Leverage, and Profitability Ratios

```python
# File: src/ai_finance_course/skills/financial_model.py
def current_ratio(financials: FinancialStatements) -> float:
    """Liquidity: can short-term assets cover short-term liabilities?"""
    return financials.current_assets / financials.current_liabilities


def debt_to_equity(financials: FinancialStatements) -> float:
    """Leverage: how much debt/liability financing per dollar of equity."""
    return financials.total_liabilities / financials.total_equity


def return_on_equity(financials: FinancialStatements) -> float:
    return financials.net_income / financials.total_equity
```

Each ratio is one pure function, philosophy-agnostic — any future skill can call these directly rather than recomputing them.

## 2.3 Calculating All Ratios at Once

```python
def calculate_all_ratios(financials: FinancialStatements) -> dict[str, float]:
    return {
        "current_ratio": current_ratio(financials),
        "debt_to_equity": debt_to_equity(financials),
        "return_on_equity": return_on_equity(financials),
        "return_on_assets": return_on_assets(financials),
        "net_margin": net_margin(financials),
    }
```

This is exactly what feeds `InvestmentThesis.ratios` and the "FINANCIAL RATIOS" block of Day 1's prompt.

## Day 2 Activity

Using a `FinancialStatements` you make up, calculate all five ratios by hand and compare against `calculate_all_ratios`.

---

# Day 3: Building the DCF Model in Excel with Python

## 3.1 DCF Assumptions: One Source of Truth

```python
# File: src/ai_finance_course/skills/dcf_model.py
class DCFAssumptions(BaseModel):
    base_revenue: float
    revenue_growth_rates: list[float]  # one rate per projected year
    ebit_margin: float
    tax_rate: float
    da_pct_revenue: float
    capex_pct_revenue: float
    nwc_change_pct_revenue: float
    wacc: float
    terminal_growth_rate: float
    shares_outstanding: float
    net_debt: float
    current_share_price: float
```

Every number the model needs lives here — nothing downstream hardcodes a value, the same "no magic numbers" principle Week 2 §3.2 taught for code comments, applied to a financial model instead.

## 3.2 Projecting Revenue and Free Cash Flow

```python
def project_revenue(base_revenue: float, growth_rates: list[float]) -> list[float]:
    revenues = []
    previous = base_revenue
    for rate in growth_rates:
        previous = previous * (1 + rate)
        revenues.append(previous)
    return revenues


def unlevered_fcf(revenues, ebit_margin, tax_rate, da_pct_revenue, capex_pct_revenue, nwc_change_pct_revenue):
    fcf = []
    for revenue in revenues:
        ebit = revenue * ebit_margin
        nopat = ebit * (1 - tax_rate)
        da = revenue * da_pct_revenue
        capex = revenue * capex_pct_revenue
        nwc_change = revenue * nwc_change_pct_revenue
        fcf.append(nopat + da - capex - nwc_change)
    return fcf
```

These are pure functions — no Excel, no I/O — so Day 5 tests them directly against hand-computed numbers.

## 3.3 Discounting and Terminal Value

```python
def discount_factors(wacc: float, num_years: int) -> list[float]:
    return [1 / (1 + wacc) ** year for year in range(1, num_years + 1)]


def terminal_value(final_year_fcf: float, wacc: float, terminal_growth_rate: float) -> float:
    """Gordon growth terminal value as of the end of the final projected year."""
    return final_year_fcf * (1 + terminal_growth_rate) / (wacc - terminal_growth_rate)
```

`intrinsic_value_per_share` combines all of the above: sum the discounted FCFs, add the discounted terminal value, subtract net debt, divide by shares outstanding. Read the full function in `dcf_model.py`.

This connects straight back to the Value Investor philosophy: **margin of safety** (§4.2) is just this intrinsic value compared against the current market price.

## 3.4 Writing Live Formulas with `openpyxl`

The deliverable isn't only a Python calculation — it's a real Excel workbook a user can open and audit. `openpyxl` writes actual formulas, not frozen numbers:

```python
ws[f"{col}2"] = f"={prior_revenue}*(1+{growth_cell})"       # Revenue
ws[f"{col}3"] = f"={col}2*Assumptions!$B${_EBIT_MARGIN_ROW}"  # EBIT
ws[f"{col}9"] = f"=1/(1+Assumptions!$B${_WACC_ROW})^{col}1"   # Discount factor
```

An **Assumptions sheet** holds every input as a named cell (`Assumptions!$B$8` for WACC, etc.); the **DCF Model** sheet references those cells instead of hardcoding numbers — open the generated file in Excel, Numbers, or Google Sheets and every formula is inspectable, not a black box.

## 3.5 Why No `NPV()`/`IRR()`

Excel's built-in `NPV()`/`IRR()` functions hide the year-by-year math inside one function call — harder to audit, and (relevant for Day 5) not supported by every formula engine. Every formula in this workbook uses only plain arithmetic and `SUM`, so each year's discounting is a visible, checkable cell.

## Day 3 Activity

Open a generated workbook (build one by running `python examples/week-17/evaluate_company.py`, once Day 6's example exists) and change one assumption — the WACC, say — directly in Excel. Confirm the intrinsic value per share updates automatically.

---

# Day 4: Catalysts, Bull/Bear Case, and Mapping the Timeline

## 4.1 The Catalyst Model

```python
class Catalyst(BaseModel):
    description: str
    timeframe: str
    direction: Literal["bull", "bear"]
```

The prompt (§1.4) instructs the LLM to return catalysts in chronological order, nearest-term first — the rendering in §4.3 depends on that ordering rather than trying to parse arbitrary date strings like "Q1 2027" or "next 12–24 months".

## 4.2 Tying the Thesis to the Margin of Safety

```python
ratios = calculate_all_ratios(financials)
intrinsic_value = intrinsic_value_per_share(dcf_assumptions)
margin = margin_of_safety_pct(intrinsic_value, dcf_assumptions.current_share_price)
```

These three values — ratios, intrinsic value, margin of safety — are computed in Python, not asked of the LLM, and passed into the prompt as evidence. The LLM forms the bull/bear case and catalysts; it doesn't recompute the valuation.

## 4.3 Rendering the Catalyst Timeline

```python
def render_catalyst_timeline(thesis: InvestmentThesis) -> Figure:
    fig, ax = plt.subplots(figsize=(width, 5))
    ax.axhline(0, color="black", linewidth=1)
    for i, catalyst in enumerate(thesis.catalysts):
        y = 1 if catalyst.direction == "bull" else -1
        ax.plot([i, i], [0, y], ...)
        ax.annotate(textwrap.fill(catalyst.description, width=28), xy=(i, y), ...)
    ax.set_xticklabels([c.timeframe for c in thesis.catalysts], rotation=30, ha="right")
    ...
```

Bull catalysts plot above the line, bear catalysts below — a real bug surfaced while building this: with several catalysts close together, their text labels overlapped into unreadable text. The fix staggers each side's annotations progressively farther from the line and wraps long descriptions across multiple lines (`textwrap.fill`), rather than assuming one fixed offset works for every case.

## Day 4 Activity

Build an `InvestmentThesis` by hand with four catalysts (two bull, two bear) and render its timeline. Confirm the labels don't overlap.

---

# Day 5: Testing the Model

## 5.1 Testing Pure Functions

```python
# File: tests/test_dcf_model.py
def test_project_revenue() -> None:
    revenues = project_revenue(1000.0, [0.10, 0.10])
    assert revenues == pytest.approx([1100.0, 1210.0])
```

Same approach as every prior week: hand-compute the expected numbers, assert against them, no Excel or network involved.

## 5.2 Recalculating Excel Formulas

Structural checks (the right cells exist) don't prove a formula is *correct*. `formulas` — a pure-Python Excel engine — actually recalculates the generated workbook:

```python
def test_dcf_workbook_formulas_match_python(tmp_path) -> None:
    path = tmp_path / "dcf.xlsx"
    build_dcf_workbook(ASSUMPTIONS, str(path))

    xl_model = formulas.ExcelModel().loads(str(path)).finish()
    solution = xl_model.calculate()

    sheet_key = f"'[{path.name}]DCF MODEL'!"
    recalculated_ivps = solution[f"{sheet_key}B19"].value[0, 0]

    assert recalculated_ivps == pytest.approx(intrinsic_value_per_share(ASSUMPTIONS))
```

This is why §3.5 avoided `NPV()`/`IRR()` — `formulas` recalculates plain arithmetic and `SUM` reliably; exotic functions are a gamble.

## 5.3 Testing `evaluate_company` with a Stub

```python
# File: tests/test_value_investor.py
def test_evaluate_company_with_stub() -> None:
    def stub_generate(prompt: str) -> str:
        return json.dumps(CANNED_RESPONSE)

    thesis = evaluate_company("DEMO", EVIDENCE, FINANCIALS, DCF_ASSUMPTIONS, stub_generate)

    assert thesis.intrinsic_value_per_share == pytest.approx(intrinsic_value_per_share(DCF_ASSUMPTIONS))
```

No API key, no real LLM call, no network — the same injected-callable pattern from Week 5's `httpx.MockTransport` tests, applied to an LLM instead of an HTTP client.

## Day 5 Activity

Write one more test: a stub `generate` that returns JSON wrapped in a ` ```json ` code fence, and confirm `evaluate_company` still parses it (this is a real thing LLMs do — `_extract_json` in `value_investor.py` handles it).

---

# Day 6: Wiring the Claude Skill Wrapper and Wrap-Up

## 6.1 What Is a Claude Skill?

A Claude Skill is a `SKILL.md` file — frontmatter (`name`, `description`) plus instructions — that Claude Code loads and follows when a request matches its description. This project already uses several (`/run`, `/code-review`, etc.); `.claude/skills/investment-philosopher/SKILL.md` is this repository's first **project-local** one.

## 6.2 Writing `SKILL.md`

The wrapper is deliberately thin — it points at the tested Python module rather than re-describing the analysis logic:

```markdown
---
name: investment-philosopher
description: Evaluate a company as a value investor (Graham/Buffett-style)
  would — thesis, bull/bear case, catalyst timeline, ratio analysis, and a
  DCF valuation. Use when the user asks to evaluate, analyze, or form an
  investment thesis on a stock/company using a specific investment philosophy.
---

# Investment Philosopher

This is a thin wrapper around `src/ai_finance_course.skills` — a tested
Python package, not a reimplementation. Reuse it; don't recreate the
analysis logic in the response.
...
```

A good `description` matters more than it looks — it's what Claude Code matches against a user's request to decide whether to use the skill at all.

## 6.3 Running the Full Example

```bash
python examples/week-17/evaluate_company.py
```

This calls a real LLM (requires `LLM_API_KEY`/`LLM_MODEL` in `.env`), prints the thesis, saves `catalyst_timeline.png`, and saves `dcf_model.xlsx`. Two real bugs surfaced building this, worth knowing about generally:

- Some models return a `thinking` content block *before* the `text` block — code that assumes `content[0]` is always the answer will crash. Find the block by `type`, not position.
- `max_tokens` has to budget for thinking tokens *and* the full JSON response — too low truncates the response mid-JSON, which then fails to parse.

## Day 6 Activity

Write a short reflection: what did you build, what failed, how did you fix it, and how would you explain this skill's architecture in an interview?

---

# Week 17 Coding Lab

## The Value Investor Skill

Extend [`src/ai_finance_course/skills/`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/ai_finance_course/skills) and its tests:

- confirm `financial_model.py`'s five ratios and `dcf_model.py`'s DCF functions are all tested against hand-computed values;
- confirm the Excel-recalculation test in `test_dcf_model.py` passes;
- confirm `value_investor.py`'s `evaluate_company` and `render_catalyst_timeline` are tested with a stub `generate`;
- set `LLM_API_KEY`/`LLM_MODEL` in your own `.env` and run [`examples/week-17/evaluate_company.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/examples/week-17/evaluate_company.py) for real;
- confirm `.claude/skills/investment-philosopher/SKILL.md` exists and its `description` would actually match a request like "evaluate AAPL as a value investor."

### Required Features

- type hints and a docstring on every function, following Week 2 §3.2's comment rules;
- pure calculation logic (ratios, DCF math) kept separate from I/O (Excel writing, the LLM call) and network calls;
- every pure function has at least one test with hand-computed expected values;
- the generated Excel workbook is verified by recalculation, not just structural checks;
- no API keys, tokens, or `.env` files committed;
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: A New Ratio

Add a quick ratio (e.g. `asset_turnover = revenue / total_assets`) to `financial_model.py`, with a docstring and a test.

## Exercise 2: A Different Terminal Growth Rate

Recompute `intrinsic_value_per_share` with a terminal growth rate of `0.02` instead of `0.03`, and explain in one sentence why the result changed the direction it did.

## Exercise 3: A Sensitivity Table

Extend `build_dcf_workbook` to add a small table varying WACC by ±1% and showing the resulting intrinsic value per share for each — still using only plain formulas.

## Exercise 4: A Second Company

Change the `EVIDENCE`, `FINANCIALS`, and `DCF_ASSUMPTIONS` in `evaluate_company.py` to a different illustrative company and re-run it.

## Exercise 5: Git Practice

Make commits for `financial_model.py`, `dcf_model.py`, `value_investor.py`, and `SKILL.md` separately.

---

# Common Mistakes

## Trusting the LLM to do arithmetic

The intrinsic value, margin of safety, and ratios are computed in Python and *given* to the LLM as evidence — never ask the LLM to compute them itself and expect the number to be right.

## Using `NPV()`/`IRR()` in the workbook

Harder to audit, and risks not being supported by a recalculation engine (§3.5, §5.2). Plain arithmetic and `SUM` only.

## Assuming `content[0]` is always the LLM's answer

Some models emit a `thinking` block first (§6.3). Find the `text` block by type.

## Testing against the real LLM

Slow, costs money, and non-deterministic — a stub `generate` (§5.3) is both faster and more reliable for testing the parsing/validation logic.

## Presenting illustrative output as real diligence

The sample company, evidence, and financials in `evaluate_company.py` are fictional. Say so, every time this is shown to someone else.

---

# Interview Preparation

1. What is a "skill" in this project's sense, and why is it designed to be philosophy-agnostic where possible?
2. Why does `evaluate_company` take `generate` as a parameter instead of calling an LLM directly?
3. What's the difference between a structured financial statement snapshot and a DCF projection?
4. Why does the Excel workbook avoid `NPV()`/`IRR()`?
5. How do you verify a generated Excel file's formulas are actually correct, not just present?
6. What does "margin of safety" mean, and how is it calculated here?
7. Why does the catalyst timeline stagger annotations instead of using a fixed offset?
8. What is a Claude Skill, and how does `SKILL.md`'s `description` field get used?

---

# Week 17 Quiz

## Multiple Choice

1. Why does `FinancialStatements` exist as its own pydantic model?

   A. To make the code longer  
   B. To give financial data a structured, typed shape instead of a loose dict  
   C. To call the SEC API  
   D. To store LLM responses

2. What does `intrinsic_value_per_share` NOT do?

   A. Discount projected free cash flows  
   B. Calculate a terminal value  
   C. Call an LLM  
   D. Divide equity value by shares outstanding

3. Why does the Excel workbook avoid `NPV()` and `IRR()`?

   A. They don't exist in Excel  
   B. They hide the year-by-year math and risk not being supported by recalculation engines  
   C. They're slower than SUM  
   D. openpyxl can't write them at all

4. What does `formulas.ExcelModel().loads(...).calculate()` do in the tests?

   A. Formats the Excel file  
   B. Actually recalculates the workbook's formulas, for real verification  
   C. Deletes unused sheets  
   D. Converts the file to CSV

5. Why does `evaluate_company` accept `generate: Callable[[str], str]` instead of importing an LLM SDK?

   A. Python doesn't support SDKs  
   B. It keeps the function provider-agnostic and testable with a stub, no real API call needed  
   C. It's required by pydantic  
   D. It makes the function run faster

## Short Answer

6. Explain, in your own words, the difference between `financial_model.py` and `dcf_model.py`.

7. Why does the prompt instruct catalysts to be returned in chronological order?

8. What two real bugs came up when calling a live LLM in `evaluate_company.py`, and how were they fixed?

9. What would you need to change to add a second philosophy, e.g. a growth investor?

10. Why is illustrative sample data used in `evaluate_company.py` instead of a real company's real numbers?

---

# Week 17 Project Submission Checklist

- [ ] `src/ai_finance_course/skills/` has `base.py`, `financial_model.py`, `dcf_model.py`, `value_investor.py`.
- [ ] Every function has a docstring and type hints.
- [ ] `tests/test_financial_model.py`, `test_dcf_model.py`, `test_value_investor.py` all pass.
- [ ] The Excel-recalculation test in `test_dcf_model.py` passes.
- [ ] `examples/week-17/evaluate_company.py` and `.ipynb` run end to end with a real `LLM_API_KEY`.
- [ ] `.claude/skills/investment-philosopher/SKILL.md` exists with an accurate `description`.
- [ ] No API keys or `.env` files are committed.
- [ ] All work is committed and pushed to GitHub.

---

# Week 17 Reflection

Write 200–300 words answering:

1. What did you build this week?
2. What's the difference between testing pure functions and testing a generated Excel file?
3. What error did you encounter, and how did you fix it?
4. Why does this skill take evidence and financials as parameters instead of fetching them itself?
5. What would you improve, or what philosophy would you build next?

Save as:

```text
week17_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Skill | A self-contained module implementing one process for evaluating something |
| Investment thesis | A structured view on a company: summary, bull case, bear case, catalysts |
| Catalyst | A specific, dated event that could move a stock |
| Margin of safety | How far below intrinsic value the current price sits |
| DCF | Discounted cash flow — a valuation method based on projected future cash flows |
| Terminal value | The value of all cash flows beyond the explicit projection period |
| `openpyxl` | A Python library for reading/writing real Excel workbooks, including formulas |
| `formulas` | A pure-Python Excel formula engine, used here to verify generated workbooks |
| Claude Skill | A `SKILL.md` file Claude Code loads and follows when a request matches its description |

---

# Week Summary

During Week 17, you:

- designed a philosophy-agnostic skill architecture around shared types and a `Protocol`;
- wrote an evidence-based LLM prompt following Week 6's role/task/evidence/constraints/output-format structure;
- built a typed financial statement snapshot and calculated standard ratios from it;
- built a multi-year DCF model as pure, tested Python functions;
- generated a real, formula-driven Excel workbook and verified it by actually recalculating it;
- rendered a bull/bear catalyst timeline with matplotlib, fixing a real label-overlap bug;
- tested LLM-calling code with a stub, and fixed two real bugs calling a live model;
- wrapped the whole skill in a thin Claude Skill (`SKILL.md`).

---

# Suggested Reading

## Required

- openpyxl documentation, "Simple usage" and "Formulas"
- Anthropic API documentation, "Messages"
- Benjamin Graham, *The Intelligent Investor* (concepts referenced: margin of safety, intrinsic value)

## Recommended

- Aswath Damodaran, *Investment Valuation* (DCF and terminal value)
- Claude Code documentation on Skills (`SKILL.md` format and discovery)

---

# Where to Go From Here

This week built one skill. The architecture (`base.py`'s shared types and `InvestmentPhilosophy` protocol, `financial_model.py`'s ratios, `dcf_model.py`'s valuation) was deliberately kept philosophy-agnostic so a second one is mostly new prompt-writing, not new infrastructure. Natural next steps:

- A **growth investor** skill: different prompt emphasis (revenue acceleration, TAM expansion), same shared types.
- A **dividend investor** skill: add a dividend-discount-model variant alongside `dcf_model.py`.
- Wire the skill into a capstone's FastAPI app (Week 14) as a `POST /evaluate` endpoint.
- Extend the DCF workbook with the sensitivity table from Practice Exercise 3.

This is the last week in the course as currently written — from here, extending it is the exercise.
