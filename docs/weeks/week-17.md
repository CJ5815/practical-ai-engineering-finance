# Week 17: Investment Philosophy Skills

> **Full lesson content:** This page is the day-by-day schedule and checklist. For the complete lesson — concept explanations, guided code walkthroughs, exercises, and the quiz — see [week-17_Practical_AI_Engineering_for_Finance.md](week-17_Practical_AI_Engineering_for_Finance.md).

## Objective

Build a reusable "skill" implementing an investment philosophy's process for
evaluating a stock: an evidence-based thesis, a bull/bear case, a
time-mapped catalyst path, financial ratio analysis, and a multi-year DCF
valuation delivered as a real Excel workbook.

## Required Output

A tested `value_investor` skill (`src/ai_finance_course/skills/`) that takes
retrieved evidence, a financial statement snapshot, and DCF assumptions, and
produces a validated investment thesis, a catalyst timeline chart, and a
formula-driven DCF Excel workbook — plus a thin Claude Skill wrapper
(`.claude/skills/investment-philosopher/SKILL.md`) that invokes it directly.

This is an **optional, advanced extension** beyond the core 16-week
capstone (Week 16) — it assumes you already know the basics of DCF and
financial-statement modeling; this week is about building one
*reproducibly*, not learning what a DCF is.

## Six-Day Schedule

### Day 1 — Investment Thesis and Evidence-Based Prompting

- **0–10 minutes:** Review the capstone and open the repository.
- **10–25 minutes:** Skill architecture — shared types, the `InvestmentPhilosophy` protocol.
- **25–50 minutes:** Write the evidence-based prompt template; wire up the injected LLM call.
- **50–60 minutes:** Record notes and commit the work.

### Day 2 — Financial Statement Model and Ratio Analysis

- **0–10 minutes:** Reproduce yesterday's main idea without notes.
- **10–25 minutes:** The `FinancialStatements` model and ratio functions.
- **25–50 minutes:** Complete the ratio-analysis coding exercise.
- **50–60 minutes:** Run checks, fix errors, and commit.

### Day 3 — Building the DCF Model in Excel with Python

- **0–10 minutes:** Define the session's small deliverable.
- **10–25 minutes:** Revenue projection, unlevered FCF, discounting, terminal value.
- **25–50 minutes:** Build the Excel workbook with `openpyxl` — Assumptions sheet + live formulas.
- **50–60 minutes:** Document decisions and commit.

### Day 4 — Catalysts, Bull/Bear Case, and Mapping the Timeline

- **0–10 minutes:** Reproduce yesterday's main idea without notes.
- **10–25 minutes:** The `Catalyst` model and the matplotlib timeline chart.
- **25–50 minutes:** Tie the DCF's margin of safety into the thesis.
- **50–60 minutes:** Run checks, fix errors, and commit.

### Day 5 — Testing the Model

- **0–10 minutes:** Define the session's small deliverable.
- **10–25 minutes:** Unit-test the pure DCF and ratio functions.
- **25–50 minutes:** Recalculate the generated workbook with `formulas` and cross-check it against Python.
- **50–60 minutes:** Document decisions and commit.

### Day 6 — Wiring the Claude Skill Wrapper and Wrap-Up

- **0–10 minutes:** Review unfinished work.
- **10–25 minutes:** Write `.claude/skills/investment-philosopher/SKILL.md`.
- **25–45 minutes:** Run the full example end to end; test and improve the deliverable.
- **45–55 minutes:** Write a short reflection:
    - What did I build?
    - What failed?
    - How did I fix it?
    - How would I explain it in an interview?
- **55–60 minutes:** Push the final commit.

## Completion Checklist

- [ ] I can explain the week's main concept in plain English.
- [ ] My code runs from a clean environment.
- [ ] I did not commit API keys or private data.
- [ ] Tests or manual checks pass, including the Excel-recalculation check.
- [ ] The README or weekly notes explain what I built.
- [ ] All work is committed and pushed to GitHub.
