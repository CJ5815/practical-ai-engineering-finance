# Project: Analyst Skill Signal

## Problem

Analysts often gather strong evidence but fail to communicate a clear, decision-ready
signal. This project defines a repeatable pipeline that turns retrieved company
evidence into a structured analyst signal with explicit confidence and risk context.

## Goal

Build a reusable analyst-skill workflow that produces a clear output for a single
ticker:

- Signal (`buy`, `hold`, or `sell`)
- Confidence score
- Key supporting factors
- Key risks and invalidation conditions
- Short catalyst timeline

## Minimum Features

1. Accept structured company evidence as input.
2. Require explicit bullish and bearish evidence in output.
3. Generate a final signal with confidence and rationale.
4. Include a risk section with at least three concrete risks.
5. Include a catalyst section with near-, mid-, and long-term items.
6. Enforce a structured response schema.
7. Include tests for schema validity and output consistency.
8. Provide setup and usage instructions.

## Recommended Repository Layout

```text
src/
  ai_finance_course/
    skills/
      analyst_skill_signal.py
tests/
  test_analyst_skill_signal.py
docs/
  projects/analyst-skill-signal.md
```

## Required Documentation

The final README or project notes should explain:

- intended user;
- signal definition and assumptions;
- data and evidence inputs;
- confidence methodology;
- limitations and failure modes;
- how to run tests and reproduce results.

## Demonstration Checklist

1. Show one ticker input and the generated signal.
2. Explain why the confidence score is justified.
3. Show one case where risk evidence weakens the signal.
4. Describe one improvement you would make next.
