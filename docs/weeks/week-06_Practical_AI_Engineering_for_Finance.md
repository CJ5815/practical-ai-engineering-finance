# Week 6: Prompt Engineering

**Course:** Practical AI Engineering for Finance  
**Audience:** Senior undergraduate students  
**Schedule:** 1 hour per day, 4 days per week  
**Week Theme:** Structuring a prompt so an LLM's output is predictable, evaluable, and reusable — role, task, evidence, constraints, and output format

---

## Week Overview

Weeks 1–5 built reliable, deterministic code: a function always returns the same thing for the same input, and `EdgarClient` fails in predictable, well-defined ways. An LLM breaks that assumption — the same prompt can produce a slightly different answer each time, and a vague prompt produces wildly different answers. Prompt engineering is the discipline of writing input text that narrows an LLM's output down to something you can actually rely on.

This week establishes one convention used for the rest of the course: every prompt that asks an LLM to do real analytical work is built from five labeled parts — **ROLE, TASK, EVIDENCE, CONSTRAINTS, OUTPUT FORMAT**. You'll see this exact structure again in Week 17's `value_investor.py` and Week 20's `sec_thesis/llm/extraction.py` — both modules' docstrings literally say "follows Week 6's role/task/evidence/constraints/output-format structure." Learning it well now means recognizing it instantly later, instead of re-deriving it from scratch.

**A scope note, worth being explicit about:** this week uses your `LLM_API_KEY` for quick, exploratory calls to see how prompt changes affect real output — but the *formal*, reusable way this course calls an LLM in application code (a clean function, token/cost awareness, and pydantic validation of the response) is Week 7's job, not this week's. Think of Week 6 as learning to write the letter; Week 7 is building the mail system that sends it reliably.

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: Prompt Anatomy](#day-1-prompt-anatomy)
- [Day 2: Zero-Shot and Few-Shot Prompts](#day-2-zero-shot-and-few-shot-prompts)
- [Day 3: Structured Output](#day-3-structured-output)
- [Day 4: Prompt Comparison and Revision](#day-4-prompt-comparison-and-revision)
- [Week 6 Coding Lab](#week-6-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 6 Quiz](#week-6-quiz)
- [Week 6 Project Submission Checklist](#week-6-project-submission-checklist)
- [Week 6 Reflection](#week-6-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Next Week](#next-week)

---

# Learning Objectives

By the end of Week 6, you should be able to:

- Explain what each part of a role/task/evidence/constraints/output-format prompt contributes, and what happens if you leave one out.
- Write a zero-shot prompt and a few-shot prompt for the same task, and explain when each is the better choice.
- Ask an LLM for structured (JSON) output and parse the raw response defensively.
- Make a real API call to Claude directly via `httpx`, without an SDK.
- Compare two prompt variants on the same input and decide, with evidence, which one is better.
- Revise a prompt in response to a specific failure, rather than rewriting it from scratch.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | Prompt anatomy | A five-part prompt for the earnings-summary task |
| Day 2 | Zero-shot and few-shot prompts | A real API call comparing both styles |
| Day 3 | Structured output | A prompt returning parseable JSON |
| Day 4 | Prompt comparison and revision | A revised prompt with a documented rationale |

Each class follows the same session structure as Weeks 1–5: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: Prompt Anatomy

## 1.1 Why an LLM Needs More Structure Than a Function Call

`simple_return(100.0, 105.0)` (Week 1) always returns exactly `0.05` — the function signature *is* the contract. An LLM has no such signature. Prompt it with just `"Summarize Apple's earnings"` and you'll get a plausible-sounding paragraph that might invent numbers, guess at a quarter you didn't specify, or wander into unrelated commentary. The prompt itself has to do the job a function signature would otherwise do: state exactly what's being asked, what's known, and what the answer must look like.

## 1.2 The Five-Part Structure

Every analytical prompt in this course follows the same shape, in the same order:

```text
ROLE: Who the model should act as, and what that implies about tone and judgment.

TASK: The specific thing to do, in one or two sentences.

EVIDENCE: The actual facts/text the model must base its answer on.

CONSTRAINTS: Rules the answer must follow (what to avoid, what to require).

OUTPUT FORMAT: The exact shape the response must take.
```

Here it is filled in for a real earnings-summary task:

```python
def build_earnings_summary_prompt(ticker: str, evidence: str) -> str:
    return f"""ROLE: You are a sell-side equity research analyst writing for \
institutional clients. You are precise and never speculate beyond the evidence given.

TASK: Summarize {ticker}'s most recent quarterly earnings in three sentences or fewer.

EVIDENCE:
{evidence}

CONSTRAINTS:
- Base every claim only on the evidence above. Do not invent figures.
- Do not include any forward-looking price prediction.
- If the evidence does not mention revenue or EPS, say so explicitly rather than omitting it silently.

OUTPUT FORMAT: Return a single paragraph of plain text, no bullet points, no headers."""
```

This is the same all-caps section convention `value_investor.py` and `sec_thesis/llm/extraction.py` use — you're not learning a simplified version of the real pattern, you're learning the actual one.

## 1.3 What Each Part Actually Buys You

| Part | What it controls | What happens if you skip it |
|---|---|---|
| ROLE | Tone, level of expertise, judgment style | Generic, unfocused answers |
| TASK | Scope of the work | The model may answer a different question than you meant |
| EVIDENCE | What's true for this specific case | Fabricated facts ("hallucination") |
| CONSTRAINTS | What to avoid or require | Inconsistent formatting, speculation, unwanted content |
| OUTPUT FORMAT | Exact response shape | Output your code can't reliably parse |

## Day 1 Activity

Using the template in §1.2, write a five-part prompt for a **risk-extraction** task: given a paragraph of "Risk Factors" text from a 10-K, list the three most significant risks mentioned. Don't call the API yet — just write the prompt string and read it back as if you were the model. Does every part you wrote actually constrain the answer, or is any part just restating the task?

---

# Day 2: Zero-Shot and Few-Shot Prompts

## 2.1 Zero-Shot: No Examples

Everything in §1.2 is **zero-shot** — the model is given instructions but no worked example of a correct answer. Zero-shot is the right default: it's shorter, cheaper, and works fine for tasks with an unambiguous format (like the paragraph-of-plain-text output above).

## 2.2 Few-Shot: One or Two Examples

**Few-shot** adds one or two example input/output pairs before the real task, so the model can pattern-match the format instead of inferring it from a description alone. This matters most when the output format is unusual or the model keeps getting a specific detail wrong:

```python
def build_risk_extraction_prompt(evidence: str) -> str:
    return f"""ROLE: You are a credit risk analyst extracting risks from SEC filings.

TASK: List the three most significant risks in the evidence below.

EXAMPLE INPUT: "The Company depends on a limited number of suppliers for key components. \
Currency fluctuations could adversely affect reported results."
EXAMPLE OUTPUT:
1. Supplier concentration risk
2. Foreign currency exposure

EVIDENCE:
{evidence}

CONSTRAINTS:
- Use only the evidence above.
- Each risk must be a short phrase (5 words or fewer), not a full sentence.

OUTPUT FORMAT: A numbered list, exactly three items."""
```

Notice the example output uses short phrases, not full sentences — that's the actual behavior few-shot is steering toward here, more reliably than the CONSTRAINTS bullet alone would.

## 2.3 Your First Real Call

Both prompts above are just Python strings until something sends them to a model. Here's the direct call — the exact same pattern `examples/week-17/evaluate_company.py` and `sec_thesis`'s CLI use later, so what you type here is not a simplified stand-in:

```python
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


def call_llm(prompt: str) -> str:
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

This is deliberately a one-off script, not a permanent module — you're using it to *look at* how prompts behave, not building the reusable calling code yet. That comes in Week 7, once you've seen enough real output to know what needs validating.

## Day 2 Activity

Run the same evidence paragraph through both `build_earnings_summary_prompt`-style zero-shot and `build_risk_extraction_prompt`-style few-shot phrasing for the risk-extraction task (write a zero-shot version of it yourself first). Compare the two real responses: did the few-shot example actually change the output's format, or was it unnecessary for this particular task?

---

# Day 3: Structured Output

## 3.1 Why Ask for JSON

A paragraph of prose is fine for a human to read but painful for code to act on. Asking the model to return JSON turns its answer into something `json.loads` can parse directly into a Python object — the first step toward the model's output flowing into the rest of a program instead of just a terminal.

## 3.2 Writing the OUTPUT FORMAT Section for JSON

```python
def build_company_comparison_prompt(ticker_a: str, ticker_b: str, evidence: str) -> str:
    return f"""ROLE: You are an equity research analyst comparing two companies.

TASK: Compare {ticker_a} and {ticker_b} based only on the evidence below.

EVIDENCE:
{evidence}

CONSTRAINTS:
- Base every claim only on the evidence above. Do not invent facts.
- "stronger_pick" must be exactly "{ticker_a}", "{ticker_b}", or "unclear".

OUTPUT FORMAT: Return ONLY valid JSON, no other text, matching this shape:
{{
  "summary": "one paragraph",
  "stronger_pick": "{ticker_a}",
  "reasoning": "one sentence"
}}"""
```

"Return ONLY valid JSON, no other text" is doing real work here — without it, models commonly wrap JSON in a sentence ("Here's the comparison:") or a markdown code fence, both of which break a naive `json.loads`.

## 3.3 Parsing the Response Defensively

Even with that instruction, a code fence sometimes gets through anyway. Strip it before parsing, rather than assuming the raw response is always clean JSON:

```python
import json


def extract_json(text: str) -> str:
    """Strip a ```json fence around the response, if the model added one."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.removeprefix("json").strip()
    return stripped


raw_response = call_llm(prompt)
parsed = json.loads(extract_json(raw_response))
print(parsed["stronger_pick"])
```

This is the exact same `_extract_json`/`_extract_json` helper `value_investor.py` and `sec_thesis/llm/extraction.py` both use — you're building the real thing, in miniature.

## 3.4 What This Doesn't Solve Yet

`json.loads` confirms the response is *valid JSON* — it says nothing about whether `parsed["stronger_pick"]` is actually one of the three allowed values, or whether a key is missing entirely. Catching that requires validating the parsed dictionary against a schema, which is deliberately Week 7's topic (pydantic output validation), not this week's.

## Day 3 Activity

Run `build_company_comparison_prompt` for real, three times in a row with the same input. Confirm each response parses as valid JSON. If one doesn't, look at exactly what broke the parse — a stray sentence, a code fence, something else — and note it for Day 4.

---

# Day 4: Prompt Comparison and Revision

## 4.1 Evaluating a Prompt, Not Just Reading It

A prompt "looks reasonable" is not the same as a prompt "reliably works." Evaluate one the same way you'd evaluate code: run it more than once, on more than one input, and check the actual output against what you needed — not just whether it sounds plausible.

## 4.2 Revising in Response to a Specific Failure

Revise a prompt because of something you actually observed, not a hunch. A few concrete moves, matched to a specific symptom:

| Symptom | Revision |
|---|---|
| Output includes commentary outside the JSON | Repeat "no other text" more forcefully, or add "Do not include any explanation before or after the JSON." |
| A field sometimes has an unexpected value | Add an explicit enum-style constraint (§3.2's `stronger_pick` line) |
| Format is inconsistent between runs | Add a few-shot example showing the exact expected shape (§2.2) |
| The model speculates beyond the evidence | Strengthen the CONSTRAINTS wording — "only," "explicitly," "do not infer" read as stronger instructions than a soft suggestion |

## 4.3 Documenting Why, Not Just What

Keep a one-line rationale next to a revised prompt — "added an explicit enum constraint after 3/5 runs returned `'N/A'` instead of one of the two tickers." This is the same habit `sec_thesis/CLAUDE.md`'s engineering rules formalize later (rule 4: preserve exact evidence; rule 8: LLM output must conform to a schema) — you're practicing *why* a constraint exists, not just writing constraints by rote.

## Day 4 Activity

Take whichever prompt from this week produced the least consistent output in your own testing, revise it using §4.2's table, and re-run it the same number of times. Write one sentence stating whether the revision measurably helped.

---

# Week 6 Coding Lab

## Three Prompt Templates

Create `examples/week-06/prompt_templates.py` with three functions, each returning a complete five-part prompt string:

- `build_earnings_summary_prompt(ticker: str, evidence: str) -> str` (§1.2)
- `build_risk_extraction_prompt(evidence: str) -> str` (§2.2)
- `build_company_comparison_prompt(ticker_a: str, ticker_b: str, evidence: str) -> str` (§3.2)

Alongside it, a small script or notebook that calls each prompt for real using §2.3's `call_llm`, and for the comparison prompt, parses the JSON response using §3.3's `extract_json`.

### Required Features

- type hints and a docstring on every function, following Week 2 §3.2's comment rules;
- every prompt has all five sections (ROLE, TASK, EVIDENCE, CONSTRAINTS, OUTPUT FORMAT);
- the comparison prompt's response is actually parsed with `json.loads`, not just printed;
- `LLM_API_KEY`/`LLM_MODEL` are read from `.env`, never hard-coded (Week 5 §1.2/§1.3);
- no API keys, tokens, or `.env` files committed;
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: Swap the Role

Run `build_earnings_summary_prompt` twice — once with the ROLE as written, once with ROLE changed to "a retail investor writing a casual social media post." Compare the tone of the two real responses.

## Exercise 2: A Fourth Template

Write a fourth prompt template, `build_catalyst_prompt`, that extracts upcoming events (earnings dates, product launches) from a paragraph of evidence, returning a JSON list.

## Exercise 3: Break the JSON on Purpose

Remove the "Return ONLY valid JSON, no other text" line from the comparison prompt and run it several times. Did the model's output stop being cleanly parseable? Put the line back and confirm it's reliable again.

## Exercise 4: Three-Example Few-Shot

Extend `build_risk_extraction_prompt` to include three example input/output pairs instead of one, and compare consistency across five runs against the one-example version.

## Exercise 5: Git Practice

Make separate commits for `prompt_templates.py`, the calling script/notebook, and your Day 4 revision notes.

---

# Common Mistakes

## A vague ROLE ("You are an AI assistant")

Doesn't constrain tone, expertise, or judgment at all — it's equivalent to no role. Be specific about the persona and what it implies (§1.3).

## Missing CONSTRAINTS entirely

Without an explicit "do not invent facts" instruction, a model will often fill gaps in the evidence with plausible-sounding fabrication. This isn't a hypothetical risk — it's the single most common failure mode in evidence-based prompting.

## Assuming "Return JSON" alone is enough

Without "no other text" and (ideally) a shown example shape, models frequently wrap JSON in a sentence or a code fence. §3.2–3.3 show both the instruction and the defensive parsing that handles it anyway.

## Testing a prompt exactly once

One run tells you almost nothing about reliability. §4.1's "run it more than once" is not optional rigor — LLM output varies run to run even with identical input.

## Revising without a specific symptom in mind

"Let me just rephrase this" without knowing what actually broke tends to fix nothing and sometimes makes the format instructions muddier. §4.2's table ties each revision to an observed failure.

---

# Interview Preparation

1. What does each of the five prompt sections (ROLE, TASK, EVIDENCE, CONSTRAINTS, OUTPUT FORMAT) actually constrain?
2. When would you choose few-shot over zero-shot, and what's the cost of doing so?
3. Why does "Return ONLY valid JSON, no other text" matter even when you've already described the JSON shape?
4. What's the difference between confirming a response is valid JSON and confirming it's *correct* JSON?
5. Why keep a rationale next to a revised prompt instead of just replacing it?
6. Give a concrete example of a prompt hallucinating a fact, and which missing CONSTRAINT would have prevented it.
7. Why is this week's LLM call written as a one-off script rather than a reusable class or function?
8. How would you convince a skeptical teammate that a prompt is reliable, not just "it worked when I tried it once"?

---

# Week 6 Quiz

## Multiple Choice

1. What does the EVIDENCE section of a prompt provide?

   A. Instructions on tone  
   B. The actual facts the model must base its answer on  
   C. The exact output shape  
   D. A list of banned words

2. Why does few-shot prompting help with unusual output formats?

   A. It makes the prompt shorter  
   B. It shows the model a worked example to pattern-match against, instead of relying on a description alone  
   C. It disables the model's own judgment entirely  
   D. It guarantees valid JSON

3. What's the main risk of omitting CONSTRAINTS from an evidence-based prompt?

   A. Slower responses  
   B. The model may fabricate facts not present in the evidence  
   C. Higher API cost  
   D. The prompt becomes too short

4. Why is `json.loads` succeeding not sufficient proof a structured-output prompt is working correctly?

   A. It doesn't check that the parsed data actually matches the expected keys/values  
   B. `json.loads` doesn't exist in Python  
   C. It only works on lists, not dictionaries  
   D. It's slower than manual string parsing

5. What should trigger a prompt revision, per §4.2?

   A. A hunch that it could sound better  
   B. A specific, observed failure (inconsistent format, wrong value, fabrication)  
   C. Reaching exactly 100 words  
   D. Nothing — prompts should never be revised once written

## Short Answer

6. Explain, in your own words, why the same ROLE/TASK/EVIDENCE/CONSTRAINTS/OUTPUT FORMAT structure appears again in Week 17 and Week 20's code.

7. Why does this week's `call_llm` function get thrown away (conceptually) once Week 7 builds the real one?

8. What's the difference between a prompt that "looks reasonable" and one that's actually reliable?

9. Give one example of a CONSTRAINTS line that would prevent a specific failure you observed this week.

10. Why does §3.3's `extract_json` strip a code fence instead of just asking the model more forcefully never to use one?

---

# Week 6 Project Submission Checklist

- [ ] `examples/week-06/prompt_templates.py` has all three required prompt-building functions.
- [ ] Every prompt has all five sections (ROLE, TASK, EVIDENCE, CONSTRAINTS, OUTPUT FORMAT).
- [ ] Each prompt has been run for real against a live model at least once.
- [ ] The comparison prompt's JSON response is actually parsed with `json.loads`.
- [ ] `LLM_API_KEY`/`LLM_MODEL` are set in your own `.env` (not committed).
- [ ] You revised at least one prompt in response to an observed failure, with a documented reason.
- [ ] All work is committed and pushed to GitHub.

---

# Week 6 Reflection

Write 200–300 words answering:

1. What did you build this week?
2. Which part of the five-part structure made the biggest difference in your testing, and why?
3. What failure did you observe, and how did you revise the prompt to fix it?
4. Why does this course delay building a reusable LLM-calling function until Week 7?
5. What would you improve about one of your three prompt templates?

Save as:

```text
week6_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Role prompting | Assigning the model a persona to shape tone and judgment |
| Zero-shot | A prompt with instructions but no worked examples |
| Few-shot | A prompt that includes one or more example input/output pairs |
| Structured output | A response formatted (e.g. JSON) so code can parse it directly |
| Hallucination | Output that states something not actually supported by the given evidence |
| Prompt template | A function that builds a complete prompt string from parameters |

---

# Week Summary

During Week 6, you:

- learned the five-part role/task/evidence/constraints/output-format prompt structure used throughout the rest of this course;
- wrote and compared zero-shot and few-shot prompts for the same task;
- made your first real calls to Claude directly via `httpx`, without an SDK;
- asked a model for structured JSON output and parsed it defensively;
- evaluated a prompt's reliability across multiple runs, and revised it in response to a specific, observed failure.

---

# Suggested Reading

## Required

- Anthropic documentation, "Prompt engineering overview"
- Anthropic documentation, "Use examples (multishot prompting)"

## Recommended

- Anthropic documentation, "Increase output consistency"
- httpx documentation, "Quickstart" (a refresher on the client you're now using for a third distinct API)

---

# Next Week

## Week 7: LLM Application Basics

Week 7 introduces:

- tokens, context windows, and the cost of a real API call;
- wrapping this week's exploratory `call_llm` script into the first properly tested, reusable calling function;
- validating an LLM's JSON response against a pydantic schema, catching the gaps §3.4 flagged this week;
- failure analysis — what to do when the model's output doesn't validate.

The three prompt templates you built this week become the input to that validated calling function — you'll be reusing them, not rewriting them.
