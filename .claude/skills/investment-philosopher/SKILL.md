---
name: investment-philosopher
description: Evaluate a company as a value investor (Graham/Buffett-style) would — thesis, bull/bear case, catalyst timeline, ratio analysis, and a DCF valuation. Use when the user asks to evaluate, analyze, or form an investment thesis on a stock/company using a specific investment philosophy.
---

# Investment Philosopher

This is a thin wrapper around `src/ai_finance_course.skills` — a tested Python
package, not a reimplementation. Reuse it; don't recreate the analysis logic
in the response.

## When to use this skill

The user asks to evaluate a company/ticker as an investor would — forming a
thesis, a bull/bear case, likely catalysts, or a valuation. Currently only
one philosophy is implemented: **Value Investing** (Graham/Buffett-style —
intrinsic value, margin of safety, financial strength). Say so if the user
asks for a different philosophy (growth, dividend, etc.) — those aren't
built yet.

## What you need before running it

Ask the user for (or find in the repo) whatever of these isn't already
obvious from context:

1. **Ticker** — the company to evaluate.
2. **Evidence** — text passages about the company (filing excerpts, earnings
   call notes, news). If the user has a RAG pipeline (Weeks 9–11 of this
   course) already retrieving evidence, use its output. Otherwise ask the
   user to paste in a few passages, or use illustrative sample evidence and
   say clearly that it's illustrative, not real diligence.
3. **Financial statements** — revenue, net income, total assets, total
   liabilities, total equity, current assets, current liabilities.
4. **DCF assumptions** — base revenue, per-year growth rates, EBIT margin,
   tax rate, D&A/Capex/ΔNWC as % of revenue, WACC, terminal growth rate,
   shares outstanding, net debt, current share price. If the user hasn't
   given these, ask, or use clearly-labeled illustrative assumptions.
5. **`LLM_API_KEY`/`LLM_MODEL`** in `.env` (see `.env.example`) — required
   to actually call the LLM.

## How to run it

Write and run a short Python script (or reuse
`examples/week-17/evaluate_company.py` as a template) that:

```python
from ai_finance_course.skills.base import EvidenceChunk, FinancialStatements
from ai_finance_course.skills.dcf_model import DCFAssumptions, build_dcf_workbook
from ai_finance_course.skills.value_investor import evaluate_company, render_catalyst_timeline

# ... build EvidenceChunk list, FinancialStatements, DCFAssumptions from
# whatever the user provided ...

thesis = evaluate_company(ticker, evidence, financials, dcf_assumptions, generate=call_llm)
render_catalyst_timeline(thesis).savefig("catalyst_timeline.png")
build_dcf_workbook(dcf_assumptions, "dcf_model.xlsx")
```

`call_llm` is a small function posting to `https://api.anthropic.com/v1/messages`
with `LLM_API_KEY`/`LLM_MODEL` — see `evaluate_company.py` for the exact
shape (handle the `thinking` content-block type, and use a generous
`max_tokens`, both real bugs hit while building this skill).

## Presenting the result

Show the user, in order: the thesis summary, bull case, bear case, the
catalyst timeline (mention `catalyst_timeline.png` was generated), the
valuation (intrinsic value per share, current price, margin of safety), and
mention `dcf_model.xlsx` was generated for them to open and audit directly —
every formula in it is a live formula, not a frozen value.

## Boundaries

- Don't fabricate financial data or evidence as if real — if the user gave
  no real numbers, say the output is illustrative.
- Don't skip validation — if `evaluate_company` raises (bad JSON from the
  LLM, missing fields), surface the actual error rather than inventing a thesis.
- This is one input to an investment decision, not a substitute for real
  diligence — say so if the user seems to be treating it as the latter.