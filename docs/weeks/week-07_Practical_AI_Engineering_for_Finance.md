# Week 7: LLM Application Basics

**Course:** Practical AI Engineering for Finance  
**Audience:** Senior undergraduate students  
**Schedule:** 1 hour per day, 4 days per week  
**Week Theme:** Turning last week's exploratory prompting into a tested, reusable calling function, validated against a schema — plus the tokens/context/cost accounting real applications need

---

## Week Overview

Week 6 taught you to write a five-part prompt and read the raw text a model sends back. That's enough for exploring — it's not enough for an application, where something downstream needs to *trust* the shape of what came back without a human reading it first. This week closes that gap: your prompt-calling code becomes a small, tested, reusable function (the same shape `examples/week-17/evaluate_company.py` and `sec_thesis`'s CLI use for real), and its response gets validated against a pydantic schema instead of just eyeballed.

Along the way, this week also covers the two things every real LLM application has to account for and Week 6 deliberately skipped: **tokens** (what you're actually being charged for and what limits a single call) and **cost** (turning that into a number you can reason about before you run something expensive).

**Required output:** a script that returns a validated `CompanyResearchSummary` — reusing one of Week 6's three prompt templates, not rewriting it.

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: Tokens, Context, and Cost](#day-1-tokens-context-and-cost)
- [Day 2: Your First Reusable LLM Call](#day-2-your-first-reusable-llm-call)
- [Day 3: Pydantic Output Validation](#day-3-pydantic-output-validation)
- [Day 4: Failure Analysis and Documentation](#day-4-failure-analysis-and-documentation)
- [Week 7 Coding Lab](#week-7-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 7 Quiz](#week-7-quiz)
- [Week 7 Project Submission Checklist](#week-7-project-submission-checklist)
- [Week 7 Reflection](#week-7-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Next Week](#next-week)

---

# Learning Objectives

By the end of Week 7, you should be able to:

- Explain what a token is, roughly how text maps to token count, and why that matters for both context limits and cost.
- Estimate the dollar cost of an API call before making it.
- Turn an ad hoc prompting script into a small, documented, reusable function.
- Test LLM-calling code without a real API key, using the injected-callable pattern.
- Define a pydantic schema that constrains an LLM's structured output, and validate a real response against it.
- Read a `pydantic.ValidationError` and decide what to do about it — retry, revise the prompt, or fail loudly.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | Tokens, context, and cost | A cost-estimating function |
| Day 2 | Your first reusable LLM call | A tested `call_llm` function |
| Day 3 | Pydantic output validation | A validated `CompanyResearchSummary` |
| Day 4 | Failure analysis and documentation | A handled validation failure, documented |

Each class follows the same session structure as Weeks 1–6: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: Tokens, Context, and Cost

## 1.1 What a Token Actually Is

A **token** is the unit an LLM actually processes — roughly a word or word-piece, not exactly a character or a whole word. `"summarize"` might be one token; `"summarization"` might be split into two. You don't need to compute exact token counts by hand; the practical habit is knowing that **token count tracks length, not word count exactly**, and that both your prompt and the model's response count against the same budget.

## 1.2 The Context Window

Every model has a **context window** — the maximum number of tokens (input plus output, combined) it can handle in a single call. Week 6's evidence paragraphs were short enough this never mattered. It starts mattering the moment you pass in something long: a full 10-K section, a whole earnings call transcript. `sec_thesis` hits exactly this limit later (Week 20 truncates filing text to a fixed character budget before prompting) — that's the same constraint you're learning the shape of here, applied for real.

## 1.3 Estimating Cost Before You Spend It

Pricing is quoted per token (usually per million), and input/output tokens are often priced differently. A rough estimate, before making a call, tells you whether an experiment is going to cost a fraction of a cent or several dollars:

```python
def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    price_per_million_input: float,
    price_per_million_output: float,
) -> float:
    """Rough dollar cost estimate for one API call.

    Token counts here are estimates, not exact — this function is for
    order-of-magnitude planning, not billing reconciliation.
    """
    input_cost = (input_tokens / 1_000_000) * price_per_million_input
    output_cost = (output_tokens / 1_000_000) * price_per_million_output
    return input_cost + output_cost
```

A quick, good-enough token estimate for English prose: `len(text) / 4` characters per token. It's not exact, but it's close enough to decide "this is fine" versus "this filing needs truncating first."

## Day 1 Activity

Take the longest evidence paragraph you used in Week 6. Estimate its token count with the `len(text) / 4` rule, then call `estimate_cost` with your model's actual per-million pricing (check the provider's pricing page) and a guessed 200-token output. Is the answer closer to a fraction of a cent, or a real number you'd think twice about running a thousand times?

---

# Day 2: Your First Reusable LLM Call

## 2.1 From Script to Function

Week 6 §2.3's `call_llm` was a one-off script — fine for exploring, not something you'd want copy-pasted into five different files. Turn it into exactly one small, documented function, reused everywhere an LLM call is needed:

```python
import os

import httpx

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


def call_llm(prompt: str) -> str:
    """Call Anthropic's Messages API directly via httpx (no SDK dependency).

    Reads LLM_API_KEY and LLM_MODEL from the environment — call
    load_dotenv() once, before this function is used, not inside it.
    """
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            ANTHROPIC_MESSAGES_URL,
            headers={
                "x-api-key": os.environ["LLM_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": os.environ["LLM_MODEL"],
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()
        for block in data["content"]:
            if block["type"] == "text":
                return block["text"]
        raise ValueError(f"No text block in response: {data}")
```

This is, character for character, the same function `examples/week-17/evaluate_company.py` and `sec_thesis`'s CLI call `_call_llm` — you're not building a simplified version to replace later, this is the real one.

## 2.2 The Injected-Callable Pattern: Testing Without a Real API Key

Every function in this course that *uses* an LLM takes `generate: Callable[[str], str]` as a parameter, rather than calling `call_llm` (or any specific provider) itself:

```python
from collections.abc import Callable


def summarize_company(ticker: str, evidence: str, generate: Callable[[str], str]) -> str:
    prompt = build_research_summary_prompt(ticker, evidence)
    return generate(prompt)
```

`summarize_company` never imports `httpx` or reads `LLM_API_KEY` — so a test can pass in a small stub function instead of `call_llm`, and run in CI with no network call and no real API key at all:

```python
def test_summarize_company_uses_the_prompt() -> None:
    def stub_generate(prompt: str) -> str:
        assert "AAPL" in prompt
        return "AAPL had a strong quarter."

    result = summarize_company("AAPL", "Revenue grew 8%.", generate=stub_generate)

    assert result == "AAPL had a strong quarter."
```

This is exactly why `value_investor.py` and `sec_thesis/llm/extraction.py` are structured the way they are — you're learning the reason for the pattern, not just copying it.

## Day 2 Activity

Take one of Week 6's three prompt-building functions and write a `summarize_company`-style wrapper around it that takes `generate` as a parameter. Test it with a stub, then run it for real using §2.1's `call_llm`. Confirm both paths work.

---

# Day 3: Pydantic Output Validation

## 3.1 Defining the Schema

Week 6 §3.4 flagged the gap: `json.loads` succeeding doesn't mean the *content* is right. A pydantic model closes that gap by rejecting a response that's syntactically valid JSON but semantically wrong:

```python
from typing import Literal

from pydantic import BaseModel


class CompanyResearchSummary(BaseModel):
    ticker: str
    summary: str
    key_risks: list[str]
    sentiment: Literal["positive", "neutral", "negative"]
```

`sentiment: Literal[...]` matters more than it looks — it means a response with `"sentiment": "bullish"` fails validation immediately, instead of silently becoming a string your downstream code assumes is one of three specific values.

## 3.2 Parsing and Validating Together

```python
import json


def extract_json(text: str) -> str:
    """Strip a ```json fence around the response, if the model added one."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.removeprefix("json").strip()
    return stripped


def get_research_summary(ticker: str, evidence: str, generate) -> CompanyResearchSummary:
    prompt = build_research_summary_prompt(ticker, evidence)
    raw_response = generate(prompt)
    parsed = json.loads(extract_json(raw_response))
    return CompanyResearchSummary(**parsed)
```

Two failure points are now distinct and separately debuggable: `json.loads` raising means the model didn't return valid JSON at all; `CompanyResearchSummary(**parsed)` raising means it did, but the content didn't match the contract.

## 3.3 pydantic.ValidationError Is a ValueError

```python
import pytest

from pydantic import ValidationError


def test_rejects_invalid_sentiment() -> None:
    with pytest.raises(ValueError):  # ValidationError is a subclass of ValueError
        CompanyResearchSummary(
            ticker="AAPL",
            summary="...",
            key_risks=[],
            sentiment="bullish",  # not one of the three allowed values
        )
```

`sec_thesis/llm/extraction.py`'s own test suite catches `ValueError` for exactly this reason — you don't need to import `pydantic.ValidationError` by name if all you need is "this failed validation."

## Day 3 Activity

Construct a `CompanyResearchSummary` with an invalid `sentiment` value directly (no LLM call needed) and confirm `pytest.raises(ValueError)` catches it. Then construct one with a missing required field and read the resulting error message — which field does pydantic say is the problem?

---

# Day 4: Failure Analysis and Documentation

## 4.1 Reading a Validation Failure

A real `ValidationError` message names the exact field and the exact reason:

```text
pydantic_core._pydantic_core.ValidationError: 1 validation error for CompanyResearchSummary
sentiment
  Input should be 'positive', 'neutral' or 'negative' [type=literal_error, input_value='bullish', input_type=str]
```

That's actionable in a way a generic "something went wrong" never is — it tells you exactly which CONSTRAINTS line (Week 6 §4.2) to strengthen.

## 4.2 Deciding What to Do About a Failure

| Situation | Reasonable response |
|---|---|
| Validation fails occasionally, one field | Strengthen that field's prompt constraint (Week 6 §4.2), keep the rest |
| Validation fails most of the time | The prompt's OUTPUT FORMAT section likely needs a shown example (few-shot, Week 6 §2.2), not just a description |
| The raw response isn't JSON at all | Check whether "no other text" is present and forceful enough (Week 6 §3.2) |
| You need the call to always produce *something* usable | Retry once with the same prompt before giving up — but never silently substitute fabricated data for a failed response (this violates the same evidence-integrity principle `sec_thesis/CLAUDE.md` rule 3 states explicitly) |

## 4.3 Documenting a Failure for Next Time

Keep a short, dated note next to a prompt you had to fix: what failed, on what input, and what change resolved it. This is the same habit Week 6 §4.3 introduced — the goal is a record you or a teammate can read before repeating the same mistake, not a perfect memory of every prompt iteration.

## Day 4 Activity

Deliberately weaken one of Week 6's prompts (remove a constraint) until you can reliably reproduce a validation failure. Write down what failed, then restore the constraint and confirm it's fixed. This is the failure-analysis loop in miniature.

---

# Week 7 Coding Lab

## A Validated Company Research Summary

Create `examples/week-07/research_summary.py`:

- `call_llm(prompt: str) -> str` (§2.1) — the real, reusable calling function.
- `build_research_summary_prompt(ticker: str, evidence: str) -> str` — reuse or lightly adapt one of Week 6's three prompt templates; don't write a new one from scratch.
- `CompanyResearchSummary(BaseModel)` (§3.1).
- `get_research_summary(ticker: str, evidence: str, generate: Callable[[str], str]) -> CompanyResearchSummary` (§3.2), tested with a stub `generate` and run for real with `call_llm`.

### Required Features

- type hints and a docstring on every function, following Week 2 §3.2's comment rules;
- `get_research_summary` (and any function that calls an LLM) takes `generate` as a parameter — it never imports `httpx` or reads environment variables itself (§2.2);
- at least one test uses a stub `generate` and needs no API key or network access;
- at least one test confirms `CompanyResearchSummary` rejects an invalid `sentiment` value (§3.3);
- no API keys, tokens, or `.env` files committed;
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: Estimate Before You Run

Before running `get_research_summary` for real, estimate its cost with §1.3's `estimate_cost`, using your evidence text's length and a guessed output length. Run it for real and compare your guess to the actual token usage the API response reports (check `data["usage"]` in the raw JSON response).

## Exercise 2: A Second Validated Field

Add a `confidence: Literal["low", "medium", "high"]` field to `CompanyResearchSummary` and update the prompt's OUTPUT FORMAT section to request it.

## Exercise 3: Force and Fix a Validation Failure

Using a stub `generate` that returns a deliberately malformed response (a missing field, an invalid `sentiment`), confirm `get_research_summary` raises `ValueError`, and write the test that proves it.

## Exercise 4: A Retry Wrapper

Write a small function that calls `get_research_summary`, catches a `ValueError`, retries exactly once, and re-raises if the second attempt also fails. Test it with a stub that fails once then succeeds.

## Exercise 5: Git Practice

Make separate commits for `call_llm`/testing infrastructure, `CompanyResearchSummary`, and the retry wrapper.

---

# Common Mistakes

## Confusing token count with word count

They're close but not identical — don't assume a 1,000-word document is exactly 1,000 tokens when estimating cost or checking against a context limit (§1.1).

## Skipping cost estimation "just this once"

A single call is cheap; a loop that calls the same prompt over hundreds of filings is not. Estimate before you loop, not after the bill arrives (§1.3).

## Believing valid JSON means correct JSON

This is Week 6 §3.4's gap, restated: `json.loads` succeeding is necessary, not sufficient. §3.1–3.2 close it with a schema.

## Writing LLM-calling code that can't be tested without a real key

If a function reaches into `os.environ["LLM_API_KEY"]` itself, every test that touches it needs a real key and the network. The injected-`generate` pattern (§2.2) exists specifically so this never happens.

## Treating a validation failure as unrecoverable

A `ValidationError` is information, not a dead end — §4.1–4.2 show how to read it and decide on a specific, targeted fix.

---

# Interview Preparation

1. Why does token count matter for both cost and context-window limits, and how are those two concerns different?
2. Why is `call_llm` written as a small, separate function instead of inlined everywhere it's needed?
3. Explain the injected-callable pattern in your own words — what problem does it solve that a hardcoded LLM call doesn't?
4. What's the difference between a `json.loads` failure and a `pydantic.ValidationError`, and why does the distinction matter for debugging?
5. Why is `pydantic.ValidationError` catchable as a plain `ValueError`?
6. Give an example of a validation failure and the specific prompt change (not a full rewrite) that would fix it.
7. Why shouldn't a failed validation ever be "fixed" by substituting fabricated data?
8. How would you decide whether to retry a failed LLM call versus failing loudly?

---

# Week 7 Quiz

## Multiple Choice

1. What is a token, roughly?

   A. Exactly one word  
   B. Exactly one character  
   C. A word or word-piece unit the model actually processes  
   D. A unit of API cost only, unrelated to context limits

2. What does the context window limit?

   A. Only the number of API calls per day  
   B. The combined input and output tokens a single call can handle  
   C. Only the cost of a call  
   D. The number of prompt templates you can define

3. Why does `get_research_summary` take `generate: Callable[[str], str]` as a parameter?

   A. To make the function slower  
   B. So it can be tested with a stub, with no real API key or network call needed  
   C. Because pydantic requires it  
   D. It doesn't need to; this is unnecessary complexity

4. What does `pydantic.ValidationError` being a subclass of `ValueError` let you do?

   A. Ignore validation entirely  
   B. Catch it with `except ValueError`, without importing pydantic's own exception type  
   C. Skip writing tests for it  
   D. Nothing; the inheritance is irrelevant

5. Which situation calls for retrying the same LLM call once, per §4.2's table?

   A. Every single failure, no matter the cause  
   B. Only when there's a specific, identified reason to think a retry might succeed, and never as a substitute for fixing the prompt  
   C. Never — always fail immediately  
   D. Only when the API key is invalid

## Short Answer

6. Explain, in your own words, why `call_llm` never appears inside `get_research_summary`'s own signature or body.

7. Why is `len(text) / 4` a reasonable rough token estimate, and why isn't it exact?

8. What's one concrete difference between how Week 6 and Week 7 treat the same LLM call?

9. Why does a validation error message naming the exact field matter for how you'd fix the prompt?

10. What would you check first if `get_research_summary` started failing validation on every call, after working fine yesterday?

---

# Week 7 Project Submission Checklist

- [ ] `examples/week-07/research_summary.py` has `call_llm`, `build_research_summary_prompt`, `CompanyResearchSummary`, and `get_research_summary`.
- [ ] `get_research_summary` (and any LLM-calling function) takes `generate` as a parameter rather than calling a provider directly.
- [ ] At least one test uses a stub `generate` and needs no API key.
- [ ] At least one test confirms an invalid `sentiment` value raises `ValueError`.
- [ ] `get_research_summary` has been run for real against a live model at least once.
- [ ] You estimated cost before running a real call (§1.3).
- [ ] `LLM_API_KEY`/`LLM_MODEL` are set in your own `.env` (not committed).
- [ ] All work is committed and pushed to GitHub.

---

# Week 7 Reflection

Write 200–300 words answering:

1. What did you build this week?
2. Why does `get_research_summary` take `generate` as a parameter instead of calling `call_llm` directly?
3. What validation failure did you observe, and how did you fix its root cause?
4. Why does token/cost estimation matter before running something at scale, even if a single call is cheap?
5. What would you improve about `CompanyResearchSummary`'s schema?

Save as:

```text
week7_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Token | The unit of text an LLM processes; roughly a word or word-piece |
| Context window | The maximum combined input+output tokens a single call can handle |
| Injected-callable pattern | Passing a function (e.g. `generate`) as a parameter instead of hardcoding a dependency |
| Schema validation | Checking parsed data against a defined structure (here, a pydantic `BaseModel`) |
| `Literal` type | A type hint restricting a field to a fixed set of exact values |
| `ValidationError` | The exception pydantic raises when data doesn't match a model's schema |

---

# Week Summary

During Week 7, you:

- learned what a token is and why it drives both context limits and cost;
- estimated the dollar cost of an API call before making it;
- turned Week 6's exploratory prompting script into a small, reusable, documented `call_llm` function;
- adopted the injected-callable pattern, testing LLM-calling code with a stub instead of a real API key;
- defined a pydantic schema and validated a real LLM response against it, catching both malformed JSON and semantically wrong content;
- read a real validation failure and traced it back to a specific, fixable prompt weakness.

---

# Suggested Reading

## Required

- Anthropic documentation, "Token counting"
- Anthropic documentation, "Pricing"
- pydantic documentation, "Models" and "Error handling"

## Recommended

- pytest documentation, "Assertions about expected exceptions" (`pytest.raises`)

---

# Next Week

## Week 8: Embeddings

Week 8 introduces:

- the intuition behind embeddings — representing text as a vector so "similar meaning" becomes "close together";
- generating or loading embeddings for short financial passages;
- cosine similarity as the standard way to compare two embeddings;
- ranking passages by relevance to a user's question — the first building block toward Weeks 9–11's retrieval-augmented generation.

This is a different kind of LLM-adjacent tool than Weeks 6–7's prompting and validation — you're moving from "ask a model to reason over text you hand it" to "find the right text to hand it in the first place."
