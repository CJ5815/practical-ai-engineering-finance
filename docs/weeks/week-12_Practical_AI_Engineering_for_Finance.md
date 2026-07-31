# Week 12: Evaluation

**Course:** Practical AI Engineering for Finance  
**Audience:** Senior undergraduate students  
**Schedule:** 1 hour per day, 4 days per week  
**Week Theme:** Formalizing "did this work?" into recall, precision, and groundedness — measured on 15 real questions, with real failure modes identified, not assumed

---

## Week Overview

Week 11 measured one thing, coarsely: did retrieval find the right company at all? This week asks two sharper questions. **Recall** and **precision** ask how much of the actual relevant evidence retrieval found, and how much of what it returned was actually relevant — two different, sometimes conflicting, numbers. **Groundedness** asks whether the final answer's claims are actually supported by the evidence it cited, checked by an independent LLM judge rather than trusted on Week 10's citation-index-validity alone.

**Every number in this lesson is real.** `data/sample/eval_questions.json` was expanded from Week 11's 6 questions to a real 15-question set, each with hand-verified ground truth (`relevant_texts`, not just a ticker). Run against the real embedding model: **mean recall@3 is 93.3%, mean precision@3 is 31.1%** — and those two numbers moving in opposite directions as `k` changes is not a coincidence, it's the recall/precision trade-off working exactly as information-retrieval theory predicts. Reproduce both with [`examples/week-12/evaluation_report.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/examples/week-12/evaluation_report.py).

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: Building an Evaluation Dataset](#day-1-building-an-evaluation-dataset)
- [Day 2: Retrieval Recall and Precision](#day-2-retrieval-recall-and-precision)
- [Day 3: Groundedness and Citation Checks](#day-3-groundedness-and-citation-checks)
- [Day 4: The Evaluation Report](#day-4-the-evaluation-report)
- [Week 12 Coding Lab](#week-12-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 12 Quiz](#week-12-quiz)
- [Week 12 Project Submission Checklist](#week-12-project-submission-checklist)
- [Week 12 Reflection](#week-12-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Next Week](#next-week)

---

# Learning Objectives

By the end of Week 12, you should be able to:

- Build a labeled evaluation dataset with real, specific ground truth — not just a category label.
- Explain the difference between recall and precision, and why improving one can hurt the other.
- Compute recall@k and precision@k, and explain what each number does and doesn't tell you.
- Use an independent LLM judge to check whether an answer is actually grounded in its cited evidence.
- Produce an evaluation report and identify real failure modes from real results, not assumed ones.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | Build an evaluation dataset | A 15-question labeled set with verified ground truth |
| Day 2 | Retrieval recall and precision | `recall_at_k`/`precision_at_k`, real measured numbers |
| Day 3 | Groundedness and citation checks | A tested LLM-judge groundedness check |
| Day 4 | Create an evaluation report | A full report identifying real failure modes |

Each class follows the same session structure as Weeks 1–11: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: Building an Evaluation Dataset

## 1.1 From 6 Questions to 15, With Real Ground Truth

Week 11's question set had `{"query", "expected_ticker"}` — enough to check "did retrieval find the right company," not enough to check "did retrieval find the actual right passage." This week's `data/sample/eval_questions.json` adds a `relevant_texts` field: the exact chunk text that actually answers each question.

```json
{
  "query": "did MSFT smash analyst estimates?",
  "expected_ticker": "MSFT",
  "relevant_texts": ["Microsoft's cloud segment revenue increased sharply, offsetting softer PC sales."]
}
```

This is backward-compatible — Week 11's `hit_rate` only reads `query`/`expected_ticker` and ignores the new field entirely, so nothing from last week broke.

## 1.2 Every Question Was Verified, Not Assumed

All 15 questions were run against the real embedding model before being written into the dataset. 13 hit their target passage at rank 1; 2 didn't (the same two real misses diagnosed in Week 11: the MSFT ticker-vs-name mismatch, and the inflation vocabulary mismatch). A dataset built without checking would risk claiming ground truth for a passage retrieval can't actually find — or worse, silently building an "evaluation" that always passes because every question was accidentally easy.

## 1.3 One Relevant Passage Per Question — A Real Simplification

This corpus has 8 passages and largely one clearly-correct passage per question. Real evaluation datasets often have multiple relevant documents per question — `recall_at_k`/`precision_at_k` (Day 2) are written generically enough to handle a `relevant_texts` list of any length, even though every question in this particular dataset happens to have exactly one.

## Day 1 Activity

Add one new question to `data/sample/eval_questions.json` of your own. Before writing down its `relevant_texts`, run it against the real collection yourself and confirm which passage actually answers it — don't assume.

---

# Day 2: Retrieval Recall and Precision

## 2.1 Two Different Questions

**Recall** asks: of all the evidence that actually answers the question, how much did retrieval find? **Precision** asks: of what retrieval returned, how much of it was actually relevant? These are different questions with different failure modes — retrieval can have perfect recall and terrible precision (found the right passage, but buried it in eight irrelevant ones) or perfect precision and terrible recall (everything returned was relevant, but it missed the one passage that mattered).

## 2.2 The Code

```python
def recall_at_k(retrieved: list[dict], relevant_texts: list[str], k: int) -> float:
    top_k_texts = {chunk["text"] for chunk in retrieved[:k]}
    found = sum(1 for text in relevant_texts if text in top_k_texts)
    return found / len(relevant_texts)


def precision_at_k(retrieved: list[dict], relevant_texts: list[str], k: int) -> float:
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    relevant_set = set(relevant_texts)
    found = sum(1 for chunk in top_k if chunk["text"] in relevant_set)
    return found / len(top_k)
```

`precision_at_k` divides by `len(top_k)` — how many results were *actually* returned — not always `k`. A small corpus that has fewer than `k` chunks to return shouldn't be penalized for something it structurally can't do.

## 2.3 The Real Trade-off, Measured

```python
mean_recall_at_k:    93.3%
mean_precision_at_k: 31.1%
```

At `k=3`, recall is high (14 of 15 questions find their relevant passage somewhere in the top 3) but precision is uniformly `0.33` for every question that hits — because each question has exactly one truly relevant passage among this corpus's 8, and `k=3` always returns 3. Asking for more results is a safety net for recall (more chances to catch the right passage) that directly costs precision (more irrelevant material mixed in). Neither number alone tells the whole story — see them together.

## 2.4 A Genuinely Unrecoverable Miss (at This k)

`recall_at_k` for "are consumer price increases cooling off?" is `0.00` even at `k=3` — not just at `k=1` like Week 11 measured. The inflation passage doesn't appear anywhere in the top 3 candidates for this exact phrasing; retrieving more per this same query doesn't fix it. This is exactly why Week 11's query expansion technique exists — the fix here isn't "retrieve more," it's "ask the question differently."

## Day 2 Activity

Run `evaluate_retrieval` at `k=1`, `k=3`, and `k=5` against the real question set. Record how mean recall and mean precision each move, and explain in one sentence why they move in opposite directions.

---

# Day 3: Groundedness and Citation Checks

## 3.1 Week 10 Checked the Citation Index — Not the Claim

Week 10's `answer_question` validates that a citation number refers to evidence that actually exists (§3.3 of that lesson). It does not check whether the claim in the answer is actually *supported* by that evidence — a citation can point at a real, retrieved chunk and still be used to justify something the chunk doesn't say. That's a different, harder check, and it needs judgment, not just arithmetic.

## 3.2 An LLM Judge

```python
def build_groundedness_prompt(answer: str, cited_evidence: list[str]) -> str:
    evidence_block = "\n".join(f"[{i + 1}] {text}" for i, text in enumerate(cited_evidence))
    return f"""ROLE: You are a fact-checking auditor verifying whether an answer is \
fully supported by its cited evidence.

TASK: Determine whether the ANSWER below is fully supported by the CITED EVIDENCE. \
An answer is grounded only if every claim in it is directly stated or clearly implied \
by the evidence — not just topically related.

ANSWER: {answer}

CITED EVIDENCE:
{evidence_block}

CONSTRAINTS:
- Judge only whether the evidence supports the answer, not whether the answer is well-written.
- If any part of the answer goes beyond what the evidence states, mark it not grounded.

OUTPUT FORMAT: Return ONLY valid JSON, no other text, matching this shape:
{{"grounded": true, "reasoning": "one sentence"}}"""
```

Same Week 6 structure again. The judge is a second, independent LLM call — it never sees the model's own reasoning for producing the answer, only the answer text and the real cited evidence, so it can't simply agree with itself.

## 3.3 Real, Not Paraphrased, Evidence

```python
cited_texts = [evidence[c - 1]["text"] for c in result.citations]
check = check_groundedness(result.answer, cited_texts, generate)
```

`evidence[c - 1]["text"]` is the actual retrieved chunk — the same real-evidence-not-paraphrase principle Week 10 §4.1 established for displaying sources applies here too. The judge audits against what was actually retrieved, not against the answering model's account of what it used.

## 3.4 A Pydantic Gotcha, Caught by Testing

Building `GroundednessCheck`'s test coverage surfaced a real, easy-to-miss pydantic behavior: `bool` fields aren't strict by default. `Foo(grounded="yes", reasoning="ok")` doesn't raise — pydantic's lax coercion accepts `"yes"`/`"no"`/`"1"`/`"0"` and silently converts them to `True`/`False`. A test asserting that an invalid `grounded` value gets rejected has to use a value pydantic actually can't coerce (e.g. `"not-a-bool"`), not a string that merely isn't `True`/`False` in your head. `test_check_groundedness_rejects_invalid_response_shape` documents exactly this.

## Day 3 Activity

Read `tests/test_evaluation.py`'s comment on the `test_check_groundedness_rejects_invalid_response_shape` test. Try `Foo(grounded="1", reasoning="x")` and `Foo(grounded="banana", reasoning="x")` yourself and confirm which one pydantic accepts.

---

# Day 4: The Evaluation Report

## 4.1 One Script, Two Kinds of Metric

`examples/week-12/evaluation_report.py` runs both halves: `evaluate_retrieval` (fully deterministic, no LLM needed) across all 15 questions, then `answer_question` + `check_groundedness` (two LLM calls per question) across the same set. Splitting the report this way means a retrieval regression and a generation regression are never confused with each other — exactly Week 10 §1.2's point, now applied at evaluation scale instead of one question at a time.

## 4.2 Reading the Report

```text
=== Retrieval metrics across 15 questions ===

Mean recall@3:    93.3%
Mean precision@3: 31.1%

Retrieval failures (1):
  recall=0.00 precision=0.00  'are consumer price increases cooling off?'
```

The report doesn't just print an aggregate — `per_question` results (from `evaluate_retrieval`'s return value) let you list exactly which questions are dragging the mean down, by name, not just "recall is 93%."

## 4.3 Identifying the Three Largest Failure Modes — For Real

This week's own real run surfaces genuine failure modes worth naming precisely, not generically:

1. **Vocabulary mismatch that no amount of `k` fixes** — the inflation-cooling question, unrecoverable even at `k=3`, only fixable by rephrasing the query (Week 11).
2. **High recall, low precision by construction** — every hit question still only scores `0.33` precision at `k=3`, because this corpus has one relevant passage per question and `k=3` always returns three. A larger, more realistic corpus with genuinely multiple relevant passages per question would look different — this specific `0.33` ceiling is an artifact of this small dataset, worth stating explicitly rather than treating as a universal number.
3. **Citation validity ≠ claim groundedness** (this failure mode is a risk to check for, even where no real example was observed in this run) — Week 10 already guards against a citation pointing at nonexistent evidence; the groundedness check exists specifically to catch the harder case of a citation pointing at *real* evidence that doesn't actually say what the answer claims.

Naming failure modes this specifically — not "sometimes retrieval misses" but "vocabulary mismatch, unrecoverable at this k, on questions phrased without domain-specific terms" — is what makes an evaluation report actionable instead of just a number.

## Day 4 Activity

Run `evaluation_report.py` (or the matching notebook) with your own `LLM_API_KEY`. Read every groundedness check's `reasoning` field, and write down whether you agree with the judge's call on each — this is your own manual audit of the auditor.

---

# Week 12 Coding Lab

## Extending the Evaluation Report

This week's core code already exists and is tested — [`src/ai_finance_course/evaluation.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/ai_finance_course/evaluation.py) and [`examples/week-12/evaluation_report.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/examples/week-12/evaluation_report.py). Your lab work is to extend it:

- add at least 5 more questions to `data/sample/eval_questions.json`, each with hand-verified `relevant_texts` (Day 1's process, not assumed);
- run the full report against your extended set and record the new recall/precision/groundedness numbers;
- identify and write up (in your own words) the three largest failure modes in *your* results — they may not be the same three as this lesson's.

### Required Features

- type hints and a docstring on every function you add, following Week 2 §3.2's comment rules;
- every new eval question's ground truth is verified against real retrieval, not assumed;
- confirm `pytest` still passes, including the pydantic-coercion regression test;
- `LLM_API_KEY`/`LLM_MODEL` are set in your own `.env`, never hard-coded or committed;
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: Recall vs. Precision at Different k

Compute `evaluate_retrieval` at `k=1`, `3`, `5`, and `8` (the full corpus) and plot or tabulate how mean recall and mean precision each change. At what `k` does precision bottom out, and why?

## Exercise 2: A Genuinely Multi-Relevant Question

Write a question that has two truly relevant passages in the sample corpus (if one exists — check by reading `data/sample/passages.json`) and confirm `recall_at_k`/`precision_at_k` handle a `relevant_texts` list of length 2 correctly.

## Exercise 3: Break the Groundedness Judge on Purpose

Write a stub `generate` for `answer_question` that produces an answer containing a claim NOT in the cited evidence (e.g., inventing a specific number). Confirm `check_groundedness` catches it, then try to construct a subtler case where the judge might be fooled.

## Exercise 4: A Second Judge Model

If you have access to two different models, run the same groundedness checks through both and compare where they disagree. Where they disagree is exactly where the check is least reliable.

## Exercise 5: Git Practice

Make separate commits for your new eval questions, your Exercise 1 k-sweep results, and your Exercise 3 write-up.

---

# Common Mistakes

## Treating high recall as "retrieval is fine"

§2.3 — high recall at a larger `k` can come with much lower precision. A system that returns 8 chunks to guarantee catching the 1 relevant one isn't necessarily healthy; it's shifted the burden onto whatever reads those 8 chunks next.

## Assuming a citation-validity check is the same as a groundedness check

§3.1 — Week 10's check confirms a citation number refers to real evidence. It says nothing about whether the claim attached to that citation is actually true according to the evidence.

## Writing eval ground truth from memory instead of verifying it

§1.2 — an evaluation dataset whose `relevant_texts` were never actually checked against real retrieval risks silently grading against the wrong answer.

## Trusting a bool field to reject non-boolean strings

§3.4 — pydantic's lax coercion accepts more string values as valid booleans than you'd expect. Test with a value that's genuinely uncoercible, not just intuitively "not a bool."

## Naming failure modes too generically to act on

§4.3 — "sometimes retrieval misses" isn't a failure mode you can fix. "Vocabulary mismatch, unrecoverable at k=3, on questions with no domain-specific terms" is.

---

# Interview Preparation

1. Explain the difference between recall and precision in your own words, with a concrete retrieval example.
2. Why does `precision_at_k` divide by the number of results actually returned, not always by `k`?
3. What's the difference between Week 10's citation-index validation and this week's groundedness check?
4. Walk through the pydantic bool-coercion gotcha found in `check_groundedness`'s tests, and why the fix mattered.
5. Why is the 0.33 precision ceiling in this week's real results specific to this dataset, not a universal number?
6. Why does the groundedness judge get only the answer and the real cited evidence, not the model's own reasoning?
7. What's one retrieval failure mode this dataset's small size can't surface, that a larger, more realistic dataset would?
8. Why does building an evaluation dataset require actually running retrieval against each question, rather than writing ground truth from memory?

---

# Week 12 Quiz

## Multiple Choice

1. What does recall@k measure?

   A. The fraction of retrieved chunks that are relevant  
   B. The fraction of known-relevant chunks that were retrieved  
   C. How fast retrieval runs  
   D. The number of chunks in the corpus

2. What does precision@k measure?

   A. The fraction of known-relevant chunks that were retrieved  
   B. The fraction of retrieved chunks that are actually relevant  
   C. The embedding model's accuracy  
   D. The number of questions in the dataset

3. Why does increasing k (retrieving more results) typically increase recall but decrease precision?

   A. It doesn't — both always increase together  
   B. More results means more chances to catch the relevant one (recall), but also more irrelevant material mixed in (precision)  
   C. k has no effect on either metric  
   D. Precision always equals recall

4. What does Week 12's groundedness check add beyond Week 10's citation validation?

   A. Nothing — they check the same thing  
   B. Confirms the answer's claims are actually supported by the cited evidence's content, not just that the citation number is valid  
   C. It replaces retrieval entirely  
   D. It checks spelling

5. What did testing `GroundednessCheck` reveal about pydantic's `bool` field?

   A. Pydantic always rejects non-boolean-typed values  
   B. Pydantic's lax coercion accepts strings like "yes"/"1" and silently converts them to True/False  
   C. Pydantic doesn't support bool fields  
   D. Bool fields require a custom validator to work at all

## Short Answer

6. Explain, in your own words, why a system with perfect recall can still have very poor precision.

7. Why does an evaluation dataset's ground truth need to be verified against real retrieval, not written from memory?

8. What real failure mode in this week's own results is "unrecoverable" by increasing k, and why?

9. Why does the groundedness judge use a separate LLM call rather than asking the same call that generated the answer to also judge itself?

10. Name one way this week's small 8-passage corpus limits what the recall/precision numbers can actually tell you.

---

# Week 12 Project Submission Checklist

- [ ] You've extended `data/sample/eval_questions.json` to at least 20 questions, each with verified `relevant_texts`.
- [ ] `examples/week-12/evaluation_report.py` runs and prints real recall@3, precision@3, and groundedness results.
- [ ] You identified and wrote up the three largest failure modes in your own results.
- [ ] `pytest` passes, including the pydantic bool-coercion regression test.
- [ ] `LLM_API_KEY`/`LLM_MODEL` are set in your own `.env` (not committed).
- [ ] All work is committed and pushed to GitHub.

---

# Week 12 Reflection

Write 200–300 words answering:

1. What did you build or extend this week?
2. Explain the recall/precision trade-off in your own words, using a number from your own run.
3. Describe the pydantic bool-coercion gotcha and why the naive test would have been wrong.
4. What were the three largest failure modes in your own evaluation results, and how did you identify them?
5. What would you improve about this week's evaluation dataset or groundedness check?

Save as:

```text
week12_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Recall | The fraction of known-relevant items that were actually retrieved |
| Precision | The fraction of retrieved items that are actually relevant |
| Ground truth | The verified correct answer(s) a system's output is checked against |
| Groundedness | Whether an answer's claims are actually supported by its cited evidence |
| LLM judge | Using a separate LLM call to evaluate another LLM output, rather than a fixed rule |
| Failure mode | A specific, named, recurring pattern of how a system produces wrong output |

---

# Week Summary

During Week 12, you:

- expanded a 6-question evaluation set into a real 15-question one, with hand-verified ground truth for every entry;
- learned the difference between recall and precision, and measured the real trade-off between them as k changes;
- built a groundedness check using an independent LLM judge, going beyond Week 10's citation-index validation to check the actual claim;
- found and fixed a real pydantic gotcha (lax bool coercion) while writing test coverage for the judge;
- produced a full evaluation report and identified specific, actionable failure modes from real results rather than assumed ones.

---

# Suggested Reading

## Required

- RAGAS documentation — already referenced in this course's [Papers and Reading](../resources/readings.md), the groundedness-check pattern here is a simplified version of what RAGAS calls "faithfulness"

## Recommended

- HELM (Holistic Evaluation of Language Models) — already in [Papers and Reading](../resources/readings.md), for a broader view of what "evaluating an LLM system" can mean beyond retrieval and groundedness

---

# Next Week

## Week 13: Testing

Week 13 introduces:

- unit tests, fixtures, and parameterization as a general testing discipline, beyond the evaluation-specific checks built this week;
- mocking external APIs, so tests never depend on a real network call or a real API key;
- integration tests spanning the API, chunking, retrieval, and answer-format components built across Weeks 6–12;
- continuous integration, so every one of these checks runs automatically, not just when you remember to run `pytest` yourself.

This week's evaluation code already has real tests — Week 13 generalizes that same discipline across the whole project.
