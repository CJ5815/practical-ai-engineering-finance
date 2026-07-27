# Week 10: Basic RAG

**Course:** Practical AI Engineering for Finance  
**Audience:** Senior undergraduate students  
**Schedule:** 1 hour per day, 4 days per week  
**Week Theme:** Combining Week 9's retrieval with Weeks 6–7's prompting and validation into one grounded, cited question-answering pipeline

---

## Week Overview

The pieces are all already built: Week 9's `query_collection` retrieves relevant chunks; Weeks 6–7's five-part prompt structure and pydantic validation turn an LLM call into something trustworthy. **Retrieval-augmented generation (RAG)** is what happens when you wire those pieces together — retrieve real evidence, build a prompt that includes it, and validate that the model's answer actually cites which evidence it used.

This week's code — `src/ai_finance_course/rag.py` — is real, committed, tested code, not something you build from a blank file. Read it, understand why it's shaped the way it is, then run [`examples/week-10/rag_assistant.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/examples/week-10/rag_assistant.py), a command-line RAG assistant over Week 9's sample passage index.

**A real bug, found live and left in this lesson on purpose:** the first version of this week's code let a model cite an evidence number that didn't exist — asking for evidence `[99]` when only 3 chunks were retrieved — and crashed with an unhandled `IndexError` the moment something tried to look that citation up. §3.3 walks through exactly what happened and how it was fixed.

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: RAG Architecture](#day-1-rag-architecture)
- [Day 2: Retrieving Context](#day-2-retrieving-context)
- [Day 3: Constructing a Grounded Prompt](#day-3-constructing-a-grounded-prompt)
- [Day 4: Returning Answers with Sources](#day-4-returning-answers-with-sources)
- [Week 10 Coding Lab](#week-10-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 10 Quiz](#week-10-quiz)
- [Week 10 Project Submission Checklist](#week-10-project-submission-checklist)
- [Week 10 Reflection](#week-10-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Next Week](#next-week)

---

# Learning Objectives

By the end of Week 10, you should be able to:

- Explain what RAG is and which parts of it are deterministic versus LLM-generated.
- Retrieve relevant context for a real question using Week 9's vector store.
- Build a grounded prompt whose EVIDENCE section comes from retrieval, not hand-written text.
- Design an output schema that asks a model to cite which evidence it used, and validate those citations against what was actually retrieved.
- Explain why trusting a model's self-reported citations without checking them is a real, exploitable gap.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | RAG architecture | Understanding how retrieval + generation fit together |
| Day 2 | Retrieve context | Real retrieval results for a real question |
| Day 3 | Construct a grounded prompt | A prompt with numbered, retrieved evidence |
| Day 4 | Return answers with sources | A validated, cited answer from the CLI assistant |

Each class follows the same session structure as Weeks 1–9: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: RAG Architecture

## 1.1 Two Halves, One Pipeline

RAG has exactly two halves, and it matters which is which:

- **Retrieval** (Week 9): fully deterministic. The same query against the same collection always returns the same chunks in the same order.
- **Generation** (Weeks 6–7): the LLM's job — reading the retrieved evidence and producing a natural-language answer, plus a self-reported list of which evidence it used.

`answer_question` in `rag.py` keeps this split explicit — it calls `query_collection` (Week 9, deterministic) to get evidence, then calls `generate` (injected, Week 7's pattern) exactly once to turn that evidence into an answer. Nothing about *which* chunks get retrieved depends on the model at all.

## 1.2 Why This Split Matters

If retrieval were somehow influenced by the model's own judgment, you'd lose the ability to test and reason about it independently — you couldn't ask "did retrieval find the right evidence?" separately from "did the model answer well given that evidence?" Keeping them separate means a bad answer can always be traced to exactly one of two causes: retrieval found the wrong evidence, or generation misused good evidence. Week 11 (Improved RAG) spends an entire week improving retrieval alone, which only makes sense because it's a separable piece.

## Day 1 Activity

Read `src/ai_finance_course/rag.py`'s module docstring and `answer_question`'s docstring in full. Without running any code, write one sentence identifying exactly where retrieval ends and generation begins in the function body.

---

# Day 2: Retrieving Context

## 2.1 Reusing Week 9's Collection

```python
from ai_finance_course.vector_store import get_or_create_collection

collection = get_or_create_collection("data/processed/chroma", "sample_passages")
```

This is the exact same collection `examples/week-09/build_passage_index.py` built — Week 10 doesn't re-embed anything or build a new index. If `data/processed/chroma` doesn't exist yet, run that script first.

## 2.2 What Gets Retrieved

```python
from ai_finance_course.vector_store import query_collection

evidence = query_collection(collection, "did the company beat earnings expectations?", n_results=3)
```

`evidence` is a list of `{"text", "metadata", "distance"}` dicts — exactly Week 9's `query_collection` return shape. This week doesn't change retrieval at all; it changes what happens to the result afterward.

## 2.3 Metadata Filtering Still Works

```python
from ai_finance_course.rag import answer_question

result, evidence = answer_question(
    "did the company beat earnings expectations?", collection, call_llm, where={"ticker": "AAPL"}
)
```

`answer_question` passes `where` straight through to `query_collection` — restricting retrieval to one company's passages restricts what evidence the model ever sees, which restricts what it can possibly cite.

## Day 2 Activity

Run a real query against the Week 9 collection (no LLM call needed yet — just `query_collection` directly) and print the retrieved evidence. Confirm the top result is actually relevant to your question before moving on to Day 3's prompt construction.

---

# Day 3: Constructing a Grounded Prompt

## 3.1 Numbering the Evidence

```python
def build_grounded_prompt(query: str, evidence: list[dict]) -> str:
    evidence_block = "\n".join(
        f"[{i + 1}] ({chunk['metadata'].get('ticker', 'unknown')}, "
        f"{chunk['metadata'].get('doc_type', 'unknown')}): {chunk['text']}"
        for i, chunk in enumerate(evidence)
    )
    return f"""ROLE: You are a financial research assistant who answers questions using \
only the evidence provided, and always cites which evidence you used.

TASK: Answer the question below using only the evidence.

QUESTION: {query}

EVIDENCE:
{evidence_block}

CONSTRAINTS:
- Base your answer only on the evidence above. Do not invent facts.
- "citations" must list the number(s) of every evidence item you actually used.

OUTPUT FORMAT: Return ONLY valid JSON, no other text, matching this shape:
{{"answer": "one or two sentences", "citations": [1, 2]}}"""
```

Same five-part structure Week 6 taught (ROLE/TASK/EVIDENCE/CONSTRAINTS/OUTPUT FORMAT) — the only thing new is that the EVIDENCE section is now *built from retrieval*, not typed by hand. Numbering each chunk (`[1]`, `[2]`, ...) is what makes citation possible at all: the model refers to evidence by number, not by repeating the text.

## 3.2 Validating the Citation Shape

```python
class RAGAnswer(BaseModel):
    answer: str
    citations: list[int]
```

Same Week 7 pattern: `json.loads` confirms the response is valid JSON, `RAGAnswer(**parsed)` confirms it has the right shape (a string and a list of integers). Neither one confirms the citations actually point at real evidence — that's a different check, and it's the one this week's real bug was missing.

## 3.3 A Real Bug: Unvalidated Citations

The first version of `answer_question` returned `RAGAnswer` as soon as it parsed and shape-validated, with no check on what the citation numbers actually meant:

```python
# The original, buggy version:
parsed = json.loads(_extract_json(raw_response))
return RAGAnswer(**parsed), evidence
```

Testing this for real — with only 3 chunks retrieved, and a response citing `[99]` — showed the actual failure: nothing in `answer_question` itself crashed, but the very first thing a caller does with a citation (`evidence[citation - 1]`, to print the source) raised an unhandled `IndexError`. The bug wasn't in the model's output being invalid JSON, and it wasn't in `RAGAnswer`'s shape being wrong — `citations: [99]` is a perfectly valid `list[int]`. The gap was one level deeper: nothing confirmed `99` referred to evidence that actually existed.

The fix checks citation numbers against the real evidence list before returning:

```python
out_of_range = [c for c in answer.citations if not (1 <= c <= len(evidence))]
if out_of_range:
    raise ValueError(
        f"Model cited evidence number(s) {out_of_range}, but only {len(evidence)} "
        "evidence chunks were retrieved."
    )
```

This is a stronger version of Week 7 §3.1's point: a schema (`list[int]`) can be perfectly valid and still be wrong in a way the schema has no way to express, because "must be between 1 and however many chunks were retrieved" depends on something the schema doesn't know at definition time — it depends on the retrieval that already happened. `test_answer_question_rejects_out_of_range_citation` in `tests/test_rag.py` is the regression test written directly from this failure.

## Day 3 Activity

Read `tests/test_rag.py`'s `test_answer_question_rejects_out_of_range_citation` test. Temporarily comment out the `out_of_range` check in `rag.py`, confirm that test now fails, then restore the check and confirm it passes again.

---

# Day 4: Returning Answers with Sources

## 4.1 Sources You Can Actually Trust

`answer_question` returns `(RAGAnswer, evidence)` — the answer *and* the real, retrieved evidence, not just the model's word for what it used:

```python
result, evidence = answer_question(question, collection, call_llm, n_results=3)

for citation in result.citations:
    chunk = evidence[citation - 1]
    print(f"[{citation}] ({chunk['metadata']['ticker']}) {chunk['text']}")
```

Printing `evidence[citation - 1]['text']` — the actual retrieved chunk — rather than trusting the model to repeat it accurately, means the source shown to a user is always real, verifiable text, never a paraphrase the model might have gotten wrong.

## 4.2 The Command-Line Assistant

```bash
python examples/week-10/rag_assistant.py "did the company beat earnings expectations?"
```

`rag_assistant.py` ties everything together: load the Week 9 collection, call `answer_question` with a real Anthropic call (`_call_llm`, the same direct-`httpx` pattern from every previous week), and print the answer followed by its sources. Read the full script — it's short, and every piece in it should already be familiar from Weeks 6, 7, and 9.

## 4.3 What "Basic" RAG Still Gets Wrong

This week's retrieval is a single, unmodified similarity search — no reranking, no query rewriting, no checking whether the *right* evidence was even retrievable in the first place. If none of the top-3 chunks are actually relevant, the model will either say so (if the CONSTRAINTS section works as intended) or, worse, answer using loosely-related evidence anyway. Week 11 exists specifically to measure and fix this.

## Day 4 Activity

Ask the CLI assistant a question the sample passages can't actually answer (e.g., something about a company not in `data/sample/passages.json`). Confirm the model either says the evidence doesn't cover it, or — if it doesn't — write down exactly what went wrong, since that's precisely the kind of failure Week 11's improvements target.

---

# Week 10 Coding Lab

## Extending the RAG Assistant

This week's core code already exists and is tested — [`src/ai_finance_course/rag.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/ai_finance_course/rag.py) and [`examples/week-10/rag_assistant.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/examples/week-10/rag_assistant.py). Your lab work is to extend it:

- ask at least five different real questions through the CLI assistant and record each answer and its sources;
- find one question where the citations are correct and one where you'd argue the model cited more (or less) evidence than it should have;
- add a metadata-filtered question (`where={"ticker": ...}`) and confirm the sources are all restricted to that ticker.

### Required Features

- type hints and a docstring on every function you add, following Week 2 §3.2's comment rules;
- any new code reuses `answer_question`/`build_grounded_prompt` rather than calling the LLM or the collection directly;
- confirm `pytest` still passes, including `test_answer_question_rejects_out_of_range_citation`;
- `LLM_API_KEY`/`LLM_MODEL` are set in your own `.env`, never hard-coded or committed;
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: Break the Fix on Purpose

Temporarily remove the `out_of_range` check in `answer_question` (§3.3) and write a stub `generate` that returns an out-of-range citation. Confirm you get an `IndexError` somewhere downstream instead of a clear `ValueError`, then restore the fix.

## Exercise 2: No Relevant Evidence

Add a question to your test set that has no good answer in `data/sample/passages.json`, and confirm the model's answer says so explicitly with an empty `citations` list, per the prompt's CONSTRAINTS section.

## Exercise 3: A Confidence Field

Add a `confidence: Literal["low", "medium", "high"]` field to `RAGAnswer` (same pattern as Week 7's `CompanyResearchSummary`) and update the prompt to request it.

## Exercise 4: Comparing n_results

Run the same question with `n_results=1` and `n_results=5`. Does giving the model more evidence change the answer's accuracy, its citations, or both?

## Exercise 5: Git Practice

Make separate commits for any new test cases, your five recorded Q&A pairs, and any schema changes.

---

# Common Mistakes

## Trusting a citation without checking it against real evidence

§3.3's bug, exactly: a citation number being a valid integer doesn't mean it's a valid *reference*. Always check it against the evidence that was actually retrieved.

## Printing the model's paraphrase instead of the real chunk

§4.1 — always print `evidence[citation - 1]['text']`, the actual retrieved text, not whatever the model repeats back, which could subtly differ from the source.

## Assuming retrieval always finds the right evidence

§4.3 — a single similarity search can miss the best-matching chunk entirely. "Basic" RAG has no mechanism to catch this; that's exactly what Week 11 adds.

## Conflating a retrieval failure with a generation failure

If an answer is wrong, check the retrieved evidence first (§1.2) — a perfectly good model can only produce a bad answer from bad evidence.

## Forgetting Week 9's index has to exist first

`rag_assistant.py` checks for `data/processed/chroma` and fails with a clear message if it's missing, rather than a confusing error deeper in the pipeline — but you still need to have run `examples/week-09/build_passage_index.py` at least once.

---

# Interview Preparation

1. Which half of RAG is deterministic, and which half depends on the model? Why does that split matter?
2. Walk through exactly how the out-of-range citation bug happened, and why a valid `list[int]` wasn't enough to catch it.
3. Why does `answer_question` return the real evidence alongside the answer, instead of just the answer?
4. What's the difference between a retrieval failure and a generation failure, and how would you tell them apart when debugging a bad answer?
5. Why is numbering evidence chunks (`[1]`, `[2]`, ...) necessary for citation to work at all?
6. What would you need to add to `RAGAnswer` to also track a confidence level?
7. Why doesn't `where={"ticker": "AAPL"}` filtering happen inside the prompt, rather than at the retrieval step?
8. What's one concrete failure mode "basic" RAG has that Week 11 is designed to fix?

---

# Week 10 Quiz

## Multiple Choice

1. Which part of a RAG pipeline is fully deterministic?

   A. The LLM's generated answer  
   B. Retrieval — the same query against the same collection always returns the same chunks  
   C. Nothing in RAG is deterministic  
   D. The citation numbers

2. What did Week 10's real bug actually involve?

   A. Invalid JSON from the model  
   B. A citation number (a valid integer) that didn't correspond to any retrieved evidence  
   C. A crash in `query_collection`  
   D. A missing API key

3. Why does `answer_question` return the retrieved evidence alongside the answer?

   A. It's required by pydantic  
   B. So a caller can display the real, verifiable source text rather than trusting the model's paraphrase  
   C. To make the function slower  
   D. It doesn't need to; the answer alone is enough

4. Why is `citations: list[int]` alone not sufficient validation?

   A. Because integers can't be validated by pydantic  
   B. Because a valid list of integers can still reference evidence numbers that don't exist  
   C. Because JSON doesn't support lists  
   D. It is sufficient; no further check is needed

5. What is "basic" RAG missing that Week 11 adds?

   A. An LLM call  
   B. Any mechanism to detect or fix a retrieval step that missed the best-matching evidence  
   C. A vector database  
   D. Metadata

## Short Answer

6. Explain, in your own words, why keeping retrieval and generation separate makes debugging a bad answer easier.

7. Why does citing evidence by number (rather than repeating its text) make grounded answers checkable?

8. What's the difference between a pydantic `ValidationError` and the `ValueError` this week's `out_of_range` check raises?

9. Why does `rag_assistant.py` check for `data/processed/chroma`'s existence before calling `answer_question`?

10. Describe one real scenario where the citations Week 10 asks for could still be wrong even after the out-of-range fix.

---

# Week 10 Project Submission Checklist

- [ ] You've read `rag.py` in full and can explain §3.3's bug in your own words.
- [ ] `examples/week-10/rag_assistant.py` runs and returns a cited answer for a real question.
- [ ] You asked at least five real questions and recorded the answers and sources.
- [ ] You found and documented at least one case of a correct citation and one debatable one.
- [ ] `pytest` passes, including `test_answer_question_rejects_out_of_range_citation`.
- [ ] `LLM_API_KEY`/`LLM_MODEL` are set in your own `.env` (not committed).
- [ ] All work is committed and pushed to GitHub.

---

# Week 10 Reflection

Write 200–300 words answering:

1. What did you build or extend this week?
2. Explain the out-of-range citation bug in your own words — what was missing, and why didn't the pydantic schema alone catch it?
3. Describe one question where retrieval found good evidence and one where it didn't. How did that affect the answer?
4. Why is it important to print the real retrieved chunk rather than trusting the model's own repetition of it?
5. What would you improve about this week's grounded prompt or citation validation?

Save as:

```text
week10_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Retrieval-augmented generation (RAG) | Combining retrieval of real evidence with LLM generation grounded in that evidence |
| Grounded prompt | A prompt whose evidence section is built from retrieval, not hand-written |
| Citation | A reference (here, a number) pointing to which retrieved evidence supports a claim |
| Schema validation | Confirming data matches a defined shape — necessary but not sufficient for correctness |
| Retrieval failure | When the retrieval step fails to surface the evidence actually needed to answer a question |

---

# Week Summary

During Week 10, you:

- combined Week 9's deterministic retrieval with Weeks 6–7's prompting and validation into one pipeline;
- built a grounded prompt whose evidence section comes from real retrieval, numbered for citation;
- traced a real bug (an unvalidated, out-of-range citation) to its root cause — a valid schema that still permitted a meaningless value — and understood the fix;
- returned answers alongside their real, verifiable source text rather than trusting a model's self-report;
- ran a real command-line RAG assistant end to end, and identified a case where "basic" retrieval falls short.

---

# Suggested Reading

## Required

- Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" — already in this course's [Papers and Reading](../resources/readings.md), the original RAG paper

## Recommended

- Liu et al., "Lost in the Middle: How Language Models Use Long Contexts" — also already in [Papers and Reading](../resources/readings.md), directly relevant to how much and which evidence to retrieve

---

# Next Week

## Week 11: Improved RAG

Week 11 introduces:

- diagnosing retrieval errors — the specific ways "basic" retrieval (this week's single similarity search) misses the right evidence;
- metadata filtering as a retrieval-quality tool, not just a convenience;
- query rewriting or expansion, to handle questions phrased differently from how the evidence is written;
- measuring improvement on a small question set — comparing this week's basic RAG against next week's improved version, with actual numbers, not just impressions.

Everything you built this week becomes the baseline Week 11 measures itself against.
