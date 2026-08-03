# Week 16: Capstone

**Course:** Practical AI Engineering for Finance
**Audience:** Senior undergraduate students
**Schedule:** 1 hour per day, 4 days per week
**Week Theme:** Integrating Weeks 1–15 into one working system, against three real public companies — no new library code, only wiring

---

## Week Overview

Every previous week added one new capability: chunking and a vector store (Week 9), retrieval-augmented generation (Week 10), evaluation (Week 12), tests (Week 13), a web API (Week 14), a real deployment (Week 15). Week 16 doesn't add a Week 16th capability — its whole job, stated plainly in the objective, is to **integrate, document, demonstrate, and reflect** on what's already built. `docs/projects/capstone.md` already defines exactly what "the complete project" means: ten minimum features, a recommended repository layout, and required documentation sections. This week is about actually assembling those already-tested pieces into that shape, not inventing anything new.

**Live-verified end to end, against real data, not a toy fixture:** [`examples/week-16/build_capstone.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/examples/week-16/build_capstone.py) makes a real HTTPS call to SEC EDGAR for three real companies (AAPL, MSFT, GOOGL — Weeks 4–5's already-tested `EdgarClient`, unchanged), indexes a new capstone dataset (`data/sample/capstone_passages.json`, 12 passages across those three companies), and runs the full Week 12 evaluation report against it: **100% mean recall@3, 33.3% mean precision@3** across 17 real evaluation questions — the same precision@3 ceiling every earlier week's evaluation hit for the identical reason (one relevant chunk out of three retrieved, by design; see §3.1).

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: Finishing Core Functionality — Mapping Capstone Requirements to What's Already Built](#day-1-finishing-core-functionality-mapping-capstone-requirements-to-whats-already-built)
- [Day 2: Running Tests and the Full Evaluation Report](#day-2-running-tests-and-the-full-evaluation-report)
- [Day 3: README, Architecture, and Repository Layout](#day-3-readme-architecture-and-repository-layout)
- [Day 4: The Five-Minute Demonstration](#day-4-the-five-minute-demonstration)
- [Week 16 Coding Lab](#week-16-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 16 Quiz](#week-16-quiz)
- [Week 16 Project Submission Checklist](#week-16-project-submission-checklist)
- [Week 16 Reflection](#week-16-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Next Week](#next-week)

---

# Learning Objectives

By the end of Week 16, you should be able to:

- Map each of `docs/projects/capstone.md`'s ten minimum features to the specific, already-tested module that implements it.
- Integrate previously separate pieces (document discovery, chunking, a vector store, RAG, evaluation) into one coherent script without writing new core logic.
- Recognize when reusing an existing fixture would silently break another week's test, and choose a separate one instead.
- Run a full evaluation report against a small, real, multi-company dataset and interpret recall@k and precision@k together, not in isolation.
- Write deployment- and architecture-level documentation for a system someone else has never seen.
- Prepare and deliver a five-minute technical demonstration, including a deliberate failure case.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | Finish core functionality | Every capstone.md minimum feature mapped to working code |
| Day 2 | Run tests and evaluations | Full `pytest` pass, a real evaluation report (`build_capstone.py`) |
| Day 3 | README and architecture diagram | Documentation covering all of capstone.md's required sections |
| Day 4 | Record demo, prepare interview explanation | A five-minute demonstration script, including one failure case |

Each class follows the same session structure as Weeks 1–15: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: Finishing Core Functionality — Mapping Capstone Requirements to What's Already Built

## 1.1 Ten Minimum Features, Ten Already-Built Answers

`docs/projects/capstone.md` lists ten minimum features. By Week 16, every one of them already has a real, tested implementation somewhere in this repository:

| Capstone requirement | Already built in |
|---|---|
| Load at least three public company documents | `edgar.py` (Weeks 4–5) — real SEC EDGAR fetch |
| Split documents into retrievable chunks | `chunking.py` (Week 9) |
| Store chunks and metadata in a vector database | `vector_store.py` (Week 9) |
| Retrieve evidence for a natural-language question | `vector_store.query_collection` (Week 9) |
| Generate an answer based only on retrieved evidence | `rag.answer_question` (Week 10) |
| Display source names or citations | `RAGAnswer.citations` (Week 10) |
| Provide at least 15 evaluation questions | `data/sample/capstone_eval_questions.json` (this week — 17 questions) |
| Include automated tests | `tests/` (Week 13, extended this week) |
| Expose the system through a CLI or FastAPI endpoint | `api.py` (Week 14) |
| Provide setup and usage instructions | `README.md` / `.env.example` (Day 3 this week) |

There is exactly one genuinely new artifact this week: `data/sample/capstone_eval_questions.json` (and its matching `capstone_passages.json`), because no earlier week needed 15+ questions across three real companies specifically. Everything else in the table is composition, not invention.

## 1.2 A Real Design Decision: a New Collection, Not the Existing One

`data/sample/passages.json` (Weeks 9–15) already has real, working, tested content for AAPL, MSFT, and a `MACRO` category. Reusing it directly for the capstone would have been less work — but Week 15's `test_ensure_sample_index_indexes_when_empty` hardcodes `assert empty_collection.count() == 8`, matching `passages.json`'s exact row count. Adding a company or a passage to that file to reach "three public companies" plus a fuller question set would have silently broken that test — not because the new content was wrong, but because a test written against one file's specific shape was never meant to tolerate that file changing shape.

The fix is a **new file and a new ChromaDB collection**: `data/sample/capstone_passages.json` (12 passages, AAPL/MSFT/GOOGL) indexed into `capstone_passages`, entirely separate from `sample_passages`. Both collections coexist in the same `data/processed/chroma` persist path without conflict — ChromaDB namespaces by collection name, not by directory alone. This is a genuinely common integration decision: when reusing an existing fixture would couple two things that should stay independent, build a new one instead of stretching the old one to cover a case it wasn't designed for.

## Day 1 Activity

Read `docs/projects/capstone.md` and `docs/projects/rubric.md` in full. For each of the ten minimum features, write down which file and function implements it — you should be able to answer this for all ten from memory by the end of Day 1.

---

# Day 2: Running Tests and the Full Evaluation Report

## 2.1 Testing the New Data, Not Just the Reused Code

```python
def test_capstone_eval_questions_relevant_texts_exist_in_passages() -> None:
    """Catches a typo or edit in either file that would silently make
    recall_at_k/precision_at_k (Week 12) always score a question as a miss."""
    passages = json.loads(PASSAGES_PATH.read_text(encoding="utf-8"))
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))

    passage_texts = {passage["text"] for passage in passages}
    for question in questions:
        for relevant_text in question["relevant_texts"]:
            assert relevant_text in passage_texts, f"{relevant_text!r} not found in capstone_passages.json"
```

`chunking.py`, `vector_store.py`, and `evaluation.py` already have their own tests from Weeks 9 and 12 — this week doesn't re-test that logic. What's new and genuinely untested until now is the **data itself**: `tests/test_capstone.py` checks that `capstone_passages.json` covers at least three tickers, that `capstone_eval_questions.json` has at least 15 entries, and — the check that actually catches real mistakes — that every `relevant_texts` entry in the question set exists verbatim in the passage set. Get this wrong (a typo, a copy-paste edit to one file without the other) and `recall_at_k`/`precision_at_k` wouldn't error — they'd just silently score every affected question as a miss, which is a much harder bug to notice than a crash.

## 2.2 The Full Evaluation Report, Against Real Multi-Company Data

```text
=== Discovering recent filings for AAPL, MSFT, GOOGL ===

AAPL:
  10-Q     2026-07-31  aapl-20260627.htm
  8-K      2026-07-30  aapl-20260730.htm
  ...

=== Indexed 12 chunks from 12 passages across 3 companies ===

=== Retrieval metrics across 17 questions ===

Mean recall@3:    100.0%
Mean precision@3: 33.3%

Retrieval failures (0):
```

This is real, live output from `examples/week-16/build_capstone.py`. Recall@3 of 100% means every question's known-relevant passage was somewhere in the top 3 retrieved results. Precision@3 of 33.3% is not a bug — with `n_results=3` and exactly one relevant chunk per question, the best any single question can score is 1 relevant out of 3 retrieved, i.e. 33.3%; averaged across all 17 questions, that ceiling is exactly what got hit. This is the same result shape Week 11 and Week 12 already explained for `sample_passages` — the capstone dataset reproduces it because the underlying cause (few relevant chunks, `n_results` fixed at 3) is unrelated to which specific dataset is indexed.

## 2.3 Graceful Degradation When `LLM_API_KEY` Isn't Set

```python
if not os.environ.get("LLM_API_KEY"):
    print("LLM_API_KEY not set — skipping generation and groundedness (set it in .env to run this part).")
    return
```

Week 12's original `evaluation_report.py` has no such check — it calls `_call_llm` unconditionally and lets a missing key raise `KeyError` partway through. That's a defensible choice for an evaluation script one person runs against their own configured environment. `docs/projects/rubric.md` grades "reliable retrieval, validation, error handling" explicitly, though, and a capstone someone else runs for the first time benefits from a clear, actionable message over a raw traceback for a section that's genuinely optional (retrieval metrics need no LLM at all). This is a small, deliberate deviation from Week 12's pattern, made for a specific, statable reason — not a blanket "always add error handling" rule.

## Day 2 Activity

Run `pytest tests/ -v` and confirm every test passes, including the five new ones in `test_capstone.py`. Then run `examples/week-16/build_capstone.py` yourself (with or without a real `LLM_API_KEY`) and read its full output, including the real EDGAR filing list for all three companies.

---

# Day 3: README, Architecture, and Repository Layout

## 3.1 What Capstone Documentation Actually Requires

`docs/projects/capstone.md`'s "Required Documentation" section is explicit: the problem, the target user, the architecture, setup instructions, example questions, evaluation results, known limitations, and future improvements. This is stricter than any previous week's documentation bar — Weeks 1–15 each documented one capability; Week 16 documents a *system*, which means explaining how the pieces fit together, not just what each piece does in isolation.

## 3.2 An Architecture Description Anyone Can Verify

A good architecture section for this project traces one request end to end: a query arrives at `/ask` (Week 14) → `get_collection()` returns the persisted ChromaDB collection (Week 9) → `query_collection` retrieves the top-k chunks → `answer_question` (Week 10) builds a grounded prompt and calls the LLM → the validated `RAGAnswer` (citations included) is returned as JSON. Anyone reading this description should be able to open the corresponding file for each arrow and confirm it does what the description says — the same "the code is the documentation" principle Week 14 §2.3 applied to FastAPI's auto-generated `/docs` page, now applied to prose written by a human.

## 3.3 Known Limitations, Stated Honestly

The capstone dataset's precision@3 ceiling (§2.2) is a real, worth-stating limitation, not something to hide: with one relevant chunk per question and `n_results=3`, precision can never exceed 33.3% under this evaluation design, regardless of how good retrieval actually is. A README that states this explicitly, with the number, is stronger evidence of understanding the system than one that omits precision entirely because the number "looks bad" out of context.

## Day 3 Activity

Write (or update) your project's `README.md` to cover every bullet in `docs/projects/capstone.md`'s "Required Documentation" section. Draft an architecture diagram — even a simple boxes-and-arrows sketch — tracing the same request path described in §3.2.

---

# Day 4: The Five-Minute Demonstration

## 4.1 The Required Structure

`docs/projects/capstone.md` specifies exactly five parts: state the problem, explain the architecture, ask one successful question, show one failure case, explain what you learned and what you'd improve. This structure is deliberate — a demo that only shows successes doesn't demonstrate understanding of the system's actual behavior, the same reasoning behind every "Common Mistakes" section in this course documenting real failures alongside real fixes.

## 4.2 Choosing a Real Failure Case, Not a Contrived One

`examples/week-16/build_capstone.py`'s own retrieval failures list (empty in this run, since recall@3 was 100%) is exactly where a real failure case would show up if one existed — a question whose relevant chunk didn't make the top 3. If your own capstone's retrieval is perfect on every question, a fair substitute failure case is `/ask` without `LLM_API_KEY` configured (Week 15 §2.3's documented, expected `500`) — a real failure mode this system actually has, not a fabricated one.

## 4.3 Explaining the Architecture Without Reading Code Aloud

Walking through §3.2's request trace in your own words — "a question comes in, gets embedded and matched against stored chunks, the matched chunks go into a prompt, the model answers only from what's in that prompt, and every claim traces back to a specific citation" — demonstrates understanding in a way that reading file names off a slide does not.

## Day 4 Activity

Record (or rehearse live) the five-minute demonstration structure from §4.1, using your own project. Time yourself — five minutes is short enough that it needs at least one practice run to fit.

---

# Week 16 Coding Lab

## Integrating Your Own Extensions

By Week 16, you may have already extended earlier weeks' work — a new `SearchRequest` field (Week 14's lab), a rate-limited `/ask` (Week 14's exercises), extra `Settings` fields (Week 15's lab). This week's lab is to confirm all of it still forms one coherent system:

- run the full `pytest` suite and confirm nothing from an earlier week's extension broke another week's test;
- run `examples/week-16/build_capstone.py` end to end, including the real EDGAR fetch;
- if you added your own capstone content beyond `capstone_passages.json`, follow §1.2's reasoning: a new collection, not a repurposed existing one, unless you've confirmed no other test depends on the existing one's exact shape.

### Required Features

- every capstone.md minimum feature (§1.1's table) works end to end, not just in isolation;
- `pytest` passes in full, including `test_capstone.py`;
- `LLM_API_KEY`/`LLM_MODEL`/`SEC_USER_AGENT` are set only in your own `.env`, never committed;
- README covers every required documentation section (§3.1);
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: A Fourth Company

Add a fourth real company's passages to a *new* file (not `capstone_passages.json` directly, per §1.2's reasoning, unless you first confirm no test depends on its exact row count) and matching evaluation questions. Re-run the evaluation report and compare recall/precision to the three-company baseline.

## Exercise 2: Breaking Referential Integrity on Purpose

Temporarily edit one word in a `capstone_passages.json` entry's text without updating the matching `relevant_texts` entry in `capstone_eval_questions.json`. Confirm `test_capstone_eval_questions_relevant_texts_exist_in_passages` catches it — then revert the change.

## Exercise 3: A Precision-Improving Change

`n_results=3` with one relevant chunk per question caps precision@3 at 33.3% (§2.2). Try `n_results=1` instead, re-run the evaluation, and explain in one sentence why recall and precision move in opposite directions when you do.

## Exercise 4: The Real EDGAR Fetch, With a Bad Ticker

Call `EdgarClient.get_filings_for_ticker` with a ticker that doesn't exist (e.g. `"ZZZZZ"`). Read the resulting error and explain, from `edgar.py`'s source, exactly which function raises it and why.

## Exercise 5: Git Practice

Make separate commits for the capstone dataset files, `build_capstone.py`, `test_capstone.py`, and your README updates.

---

# Common Mistakes

## Reusing an existing fixture without checking what depends on its exact shape

§1.2 — `passages.json`'s row count is hardcoded into a Week 15 test. A new capstone dataset avoided breaking it; changing the existing file without checking every place it's referenced would not have.

## Treating precision@k in isolation, without recall@k or the evaluation design's own ceiling

§2.2 — 33.3% precision@3 looks bad read alone; read alongside "one relevant chunk per question, three retrieved" and 100% recall@3, it's the expected, correct result, not a failure.

## A demo that only shows the happy path

§4.1 — capstone.md explicitly requires one failure case. A demonstration without one doesn't show whether the presenter understands the system's actual failure modes, only its best case.

## Documentation that omits a real limitation because the number looks unflattering

§3.3 — stating the precision@3 ceiling explicitly, with the reason, is stronger evidence of understanding than omitting it.

## Skipping the "why" when integrating already-tested pieces

§1.1 — every function in this week's script already has its own tests from earlier weeks. The new work is explaining *why* they're wired together this way, not re-explaining what each one does.

---

# Interview Preparation

1. Walk through `capstone.md`'s ten minimum features and name the specific file and function implementing each one.
2. Why does the capstone dataset use a separate ChromaDB collection instead of adding companies to `sample_passages`?
3. Explain why 33.3% mean precision@3 alongside 100% mean recall@3 is the expected, correct result for this dataset, not a sign of a problem.
4. Walk through one full request through the system, from `/ask` to a cited answer, naming every function it passes through.
5. Why does `build_capstone.py` skip the generation/groundedness section gracefully instead of crashing when `LLM_API_KEY` is unset, unlike Week 12's original script?
6. What does `test_capstone_eval_questions_relevant_texts_exist_in_passages` actually catch, and why is a silent wrong score worse than a crash?
7. What are this project's real, current limitations, and how would you improve them?
8. Why does the required five-minute demonstration structure explicitly include a failure case?

---

# Week 16 Quiz

## Multiple Choice

1. Why does `data/sample/capstone_passages.json` exist as a separate file instead of extending `passages.json`?

   A. JSON files can't be edited after creation
   B. Extending `passages.json` would change its row count and silently break a Week 15 test that hardcodes `count() == 8`
   C. ChromaDB requires a new file per collection
   D. There's no real reason; it's a style preference

2. In the capstone evaluation report, what does 100% mean recall@3 combined with 33.3% mean precision@3 indicate?

   A. Retrieval is broken
   B. Every question's relevant chunk was found in the top 3, and precision is capped at 1-in-3 by the evaluation's own design (one relevant chunk per question)
   C. The embedding model needs retraining
   D. The two metrics contradict each other and one must be wrong

3. What does `test_capstone_eval_questions_relevant_texts_exist_in_passages` protect against?

   A. Network failures during testing
   B. A typo or edit to either the passage set or the question set that would silently make recall/precision always score a miss, rather than raising an error
   C. Slow test execution
   D. Missing API keys

4. Why does `build_capstone.py` check `os.environ.get("LLM_API_KEY")` before the generation section, unlike Week 12's original script?

   A. FastAPI requires it
   B. It's a deliberate, statable choice for a capstone someone else might run for the first time — a clear message for an optional section beats a raw crash
   C. Anthropic's API requires this specific check
   D. It's required by pytest

5. What are the five required parts of the capstone's five-minute demonstration?

   A. Code walkthrough, tests, deployment, pricing, roadmap
   B. State the problem, explain the architecture, ask a successful question, show a failure case, explain what you learned and would improve
   C. Introduction, body, conclusion, Q&A, thanks
   D. Architecture only — the rest is optional

## Short Answer

6. Explain, in your own words, why Week 16 is described as adding no new library code, only integration.
7. Why is a documented, honest limitation (like the precision@3 ceiling) stronger evidence of understanding than a README that omits it?
8. What's the practical difference between a test that fails loudly (a crash) and one that fails silently (a wrong score), and why does §2.1's referential-integrity test matter more for the second kind?
9. If you were extending this capstone with a fourth company, what's the one thing §1.2's reasoning tells you to check before reusing any existing fixture?
10. Why does the architecture description in §3.2 trace a single request end to end, rather than describing each module separately?

---

# Week 16 Project Submission Checklist

- [ ] All ten of `docs/projects/capstone.md`'s minimum features work end to end.
- [ ] `data/sample/capstone_eval_questions.json` has at least 15 questions, each with a verified-real `relevant_texts` match.
- [ ] `pytest` passes in full, including `test_capstone.py`.
- [ ] `examples/week-16/build_capstone.py` runs successfully, including the real EDGAR fetch for at least three companies.
- [ ] README covers every section `docs/projects/capstone.md` requires: problem, target user, architecture, setup, example questions, evaluation results, known limitations, future improvements.
- [ ] A five-minute demonstration is prepared, following §4.1's five-part structure, including a real failure case.
- [ ] `LLM_API_KEY`/`LLM_MODEL`/`SEC_USER_AGENT` are set only in your own `.env` (never committed).
- [ ] All work is committed and pushed to GitHub.

---

# Week 16 Reflection

Write 200–300 words answering:

1. What did you build or integrate this week, beyond what any single earlier week produced alone?
2. Explain the reasoning behind creating a separate capstone dataset and collection instead of extending `sample_passages` (§1.2).
3. Describe your evaluation report's actual recall@k/precision@k results and explain what they mean, not just what they are.
4. What's the most significant known limitation of your capstone, and how would you address it given more time?
5. Describe the failure case you chose for your five-minute demonstration and what it reveals about the system.

Save as:

```text
week16_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Integration | Wiring already-built, already-tested components together, without writing new core logic |
| Referential integrity (data) | The property that references between two related files (e.g. a question's `relevant_texts` and a passage set's actual text) stay consistent |
| Precision ceiling | The maximum precision@k achievable given how many truly relevant items exist, independent of retrieval quality |
| Architecture description | A trace of one request through every component it touches, verifiable by opening the corresponding file at each step |
| Known limitation | A real, stated constraint of a system, documented honestly rather than omitted |

---

# Week Summary

During Week 16, you:

- mapped every one of `docs/projects/capstone.md`'s ten minimum features to a specific, already-tested module from Weeks 4–15;
- built a small, real capstone dataset across three real companies (AAPL, MSFT, GOOGL), deliberately kept separate from `sample_passages` to avoid silently breaking an existing test;
- ran a full, live evaluation report — a real SEC EDGAR fetch, real chunking and indexing, and real recall@3/precision@3 metrics (100% / 33.3%) — and correctly interpreted what those two numbers together actually mean;
- added tests that catch a specific, realistic integration bug: silently mismatched data between two related files;
- wrote capstone-level documentation and prepared a five-minute demonstration, including a real failure case, not just the happy path.

This closes out the core, 16-week curriculum.

---

# Suggested Reading

## Required

- `docs/projects/capstone.md` and `docs/projects/rubric.md` (this repository) — the actual requirements this week integrates against

## Recommended

- Any of Weeks 9, 10, 12, 13, 14, or 15's full lesson docs, as a refresher for the specific module you're integrating

---

# Next Week

## Week 17: Investment Philosophy Skills (Optional, Advanced)

Weeks 1–16 form the complete core curriculum. Week 17 begins an optional, advanced extension: building a reusable "skill" that evaluates a stock under a specific investment philosophy — an evidence-based thesis, financial ratio analysis, and a real, multi-year DCF model delivered as an Excel workbook. It assumes everything built through Week 16, including this week's integration work.
