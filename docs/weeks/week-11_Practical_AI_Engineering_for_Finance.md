# Week 11: Improved RAG

**Course:** Practical AI Engineering for Finance  
**Audience:** Senior undergraduate students  
**Schedule:** 1 hour per day, 4 days per week  
**Week Theme:** Diagnosing exactly why retrieval misses the right evidence, then measuring — with real numbers, not impressions — whether a fix actually helps

---

## Week Overview

Week 10 built basic RAG and flagged its own limitation honestly: a single similarity search can miss the best-matching evidence entirely, with no mechanism to notice or recover. This week measures that limitation for real, on this course's own sample passages, and fixes it with **query expansion** — asking an LLM for alternative phrasings of a question, retrieving for each, and merging the results.

**Every number in this lesson is real, not illustrative.** Before writing a line of this document, the retrieval misses described below were found by actually running queries against the real embedding model and the real Week 9 sample passages — the same discipline this course has used since Week 9's id-collision bug and Week 10's citation-validation bug. `data/sample/eval_questions.json` scores **4/6 (66.7%)** with basic retrieval and **6/6 (100%)** with query expansion — reproduce both numbers yourself with [`examples/week-11/compare_retrieval.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/examples/week-11/compare_retrieval.py).

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: Diagnosing Retrieval Errors](#day-1-diagnosing-retrieval-errors)
- [Day 2: Metadata Filtering as a Retrieval-Quality Tool](#day-2-metadata-filtering-as-a-retrieval-quality-tool)
- [Day 3: Query Expansion](#day-3-query-expansion)
- [Day 4: Comparing Basic and Improved RAG](#day-4-comparing-basic-and-improved-rag)
- [Week 11 Coding Lab](#week-11-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 11 Quiz](#week-11-quiz)
- [Week 11 Project Submission Checklist](#week-11-project-submission-checklist)
- [Week 11 Reflection](#week-11-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Next Week](#next-week)

---

# Learning Objectives

By the end of Week 11, you should be able to:

- Diagnose a specific retrieval miss by comparing what a query's embedding is close to versus what it should have found.
- Explain when metadata filtering can and can't fix a retrieval miss.
- Implement query expansion: generating alternative phrasings, retrieving for each, and merging results without duplicates.
- Build a labeled question set and compute a simple hit-rate metric across a retrieval strategy.
- Compare two retrieval strategies on the same question set with an actual measured number, not an impression.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | Diagnose retrieval errors | A documented, real retrieval miss |
| Day 2 | Metadata filtering | Understanding when filtering helps and when it can't |
| Day 3 | Query expansion | A tested `retrieve_with_expansion` |
| Day 4 | Compare basic and improved RAG | A measured hit-rate comparison |

Each class follows the same session structure as Weeks 1–10: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: Diagnosing Retrieval Errors

## 1.1 A Real Miss, Found by Testing

Querying the Week 9 sample passages with `"did MSFT smash analyst estimates?"` returns Apple's earnings passage, not Microsoft's — at `n_results=1`, that's a wrong answer, not a close second place:

```text
q='did MSFT smash analyst estimates?' expected=MSFT got=AAPL
```

## 1.2 Diagnosing, Not Just Noticing

Noticing a miss isn't the same as understanding it. The diagnosis here came from testing a hypothesis directly: does the ticker abbreviation itself confuse the embedding model?

```text
q='did MSFT smash analyst estimates?'          got=AAPL
q='did Microsoft beat earnings forecasts?'     got=MSFT
q="did Microsoft's results top expectations?"  got=MSFT
```

Swapping only `"MSFT"` for `"Microsoft"` — nothing else about the question changed — fixed the retrieval. The real cause: this course's sample passages spell out company names in full ("Microsoft's cloud segment revenue..."), and the embedding model matches full names better than ticker symbols, which look more like arbitrary strings than words with meaning. This is a genuinely useful, transferable diagnosis, not a one-off curiosity — it's why `query_expansion.py`'s prompt (§3.2) explicitly asks the model to prefer full company names.

## 1.3 A Second Real Miss: Vocabulary Mismatch

A second, different kind of miss: `"are consumer price increases cooling off?"` retrieves a Microsoft passage instead of the actual inflation passage. Here, the fix is closer wording, not a company name:

```text
q='are consumer price increases cooling off?'   got=MSFT   (wrong)
q='is inflation slowing down?'                  got=MACRO  (correct)
q='did inflation come in lower than expected?'  got=MACRO  (correct)
```

The original question never uses the word "inflation" at all — it's a real vocabulary mismatch between how the question was asked and how the evidence is written, exactly the problem query expansion (§Day 3) targets.

## Day 1 Activity

Using `data/sample/passages.json` and `query_collection` directly (no LLM needed), find one retrieval miss of your own — a question whose top result isn't the passage you'd expect. Try at least two rephrasings and note which one (if any) fixes it.

---

# Day 2: Metadata Filtering as a Retrieval-Quality Tool

## 2.1 Filtering Fixes the MSFT Miss Too — With a Catch

```python
query_collection(collection, "did MSFT smash analyst estimates?", n_results=1, where={"ticker": "MSFT"})
# -> Microsoft's cloud segment revenue increased sharply, offsetting softer PC sales.
```

Restricting the search to `ticker: "MSFT"` guarantees the top result is *some* MSFT passage — by construction, since no other ticker's passages are even considered. That's a real fix, but it comes with a real precondition: **you have to already know the ticker.**

## 2.2 When Filtering Can't Help

Compare that to a question like `"did revenue increase this quarter?"` with no company named at all. There's no ticker to filter by — the ambiguity is about *which* company the question means, not about *how* the question is phrased. Filtering is a retrieval-quality tool exactly when you have reliable structured context (a ticker already established earlier in a conversation, a document type you know you want), and it does nothing for genuine entity ambiguity in the question itself.

## 2.3 Filtering Doesn't Guarantee the *Best* Passage

Filtering the inflation-cooling question (§1.3) to `ticker: "MACRO"` does return a MACRO passage — but not necessarily the best one. With only 3 MACRO passages available, filtering can return the *closest MACRO match*, which might still be the interest-rate passage rather than the actual inflation one. Filtering guarantees the right category; it doesn't guarantee the right passage within that category. Keep this in mind for Day 4's hit-rate metric, which — deliberately, for simplicity — only checks category (ticker), not the single best passage.

## Day 2 Activity

Take a question from Day 1 that named a specific company and confirm `where={"ticker": ...}` fixes it. Then take the "no company named" question and confirm filtering genuinely can't help — there's no ticker value that would even make sense to filter by.

---

# Day 3: Query Expansion

## 3.1 The Idea

Generate a few alternative phrasings of the same question, retrieve for each one, and merge the results — if any phrasing's own vocabulary happens to match the evidence better than the original, that phrasing's results pull the right evidence into the final answer.

## 3.2 The Prompt

```python
def build_expansion_prompt(query: str) -> str:
    return f"""ROLE: You are a search-query specialist who rewrites financial research \
questions to improve retrieval from a semantic search index.

TASK: Write 2 alternative phrasings of the question below that preserve its exact \
meaning but use different wording.

QUESTION: {query}

CONSTRAINTS:
- Do not change what is being asked, only how it's phrased.
- Prefer spelling out company names in full rather than using ticker symbols \
(e.g. "Microsoft" rather than "MSFT") — full names tend to match filing text better.

OUTPUT FORMAT: Return ONLY valid JSON, no other text, matching this shape:
{{"rephrasings": ["...", "..."]}}"""
```

Same Week 6 structure, and that ticker-versus-full-name constraint is directly the diagnosis from §1.2 — a real finding turned into a real prompt instruction, not a generic best practice pasted in.

## 3.3 Merging Without Duplicates

```python
def retrieve_with_expansion(
    collection: Collection, query: str, n_results: int = 3, *, generate, where: dict | None = None
) -> list[dict]:
    queries = expand_query(query, generate)

    best_by_text: dict[str, dict] = {}
    for variant in queries:
        for result in query_collection(collection, variant, n_results=n_results, where=where):
            existing = best_by_text.get(result["text"])
            if existing is None or result["distance"] < existing["distance"]:
                best_by_text[result["text"]] = result

    return sorted(best_by_text.values(), key=lambda r: r["distance"])[:n_results]
```

`generate` is keyword-only, deliberately — it means `retrieve_with_expansion`'s positional signature `(collection, query, n_results)` matches `query_collection`'s closely enough that `retrieval_eval.hit_rate` can call either one interchangeably (via `functools.partial` to bind `generate` first). Deduplicating by `result["text"]` (keeping whichever variant found it at the lowest distance) means a chunk that three different phrasings all happen to retrieve counts once, not three times.

## 3.4 A Real Limitation, Worth Knowing

`retrieve_with_expansion` only pulls each variant's own top `n_results` into the merge pool. If `n_results=1`, only each phrasing's single best match ever gets considered — a phrasing whose *second*-best match would have been the right answer never contributes it. This isn't hypothetical: it's exactly why an early version of this week's own test suite had to be redesigned (§Day 3 Activity) after a contrived two-chunk scenario produced a tie that resolved the wrong way. Fetching more candidates per variant than the final `n_results` (Exercise 3) is one direct way to address this.

## Day 3 Activity

Read `tests/test_query_expansion.py`'s `test_retrieve_with_expansion_finds_a_variant_the_original_misses` test in full, including its comment about the distances involved. Explain in one sentence why the test asserts the *original* query's own top result first, before checking the expanded result.

---

# Day 4: Comparing Basic and Improved RAG

## 4.1 A Hit-Rate Metric

```python
def hit_rate(collection, questions, retrieve, n_results=3) -> float:
    hits = 0
    for question in questions:
        results = retrieve(collection, question["query"], n_results)
        if any(r["metadata"].get("ticker") == question["expected_ticker"] for r in results):
            hits += 1
    return hits / len(questions)
```

Deliberately simple: does *any* retrieved chunk belong to the right company? This is coarser than Week 12's full evaluation (which checks groundedness and specific claims) — good enough to compare two retrieval strategies on the same six questions, which is this week's whole point.

## 4.2 The Real Comparison

```python
basic_rate = hit_rate(collection, questions, query_collection, n_results=1)
# 66.7% (4/6)

improved_retrieve = partial(retrieve_with_expansion, generate=call_llm)
improved_rate = hit_rate(collection, questions, improved_retrieve, n_results=1)
# 100.0% (6/6)
```

`examples/week-11/compare_retrieval.py` runs exactly this, against the real embedding model and (with your own `LLM_API_KEY`) a real LLM call for query expansion. Both numbers above were verified for real before this lesson was written — run the script yourself to reproduce them.

## 4.3 What "Measurable" Actually Means Here

Two questions moved from miss to hit: the MSFT-ticker one (§1.2) and the inflation-vocabulary one (§1.3) — exactly the two misses diagnosed on Day 1. This isn't a coincidence or a cherry-picked demo: the whole exercise was diagnose two real failures first, then build a fix, then measure whether the fix addresses those specific failures. That order matters — building an "improvement" without first knowing what's actually broken is how you end up with a fix that doesn't fix anything real.

## Day 4 Activity

Run `compare_retrieval.py` (or the matching notebook) with your own `LLM_API_KEY`. Confirm your own measured numbers are close to 66.7% and 100% — small variation is expected since the LLM's exact rephrasings vary run to run, but the improvement direction should hold.

---

# Week 11 Coding Lab

## Extending the Retrieval Comparison

This week's core code already exists and is tested — [`src/ai_finance_course/query_expansion.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/ai_finance_course/query_expansion.py), [`src/ai_finance_course/retrieval_eval.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/ai_finance_course/retrieval_eval.py), and [`examples/week-11/compare_retrieval.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/examples/week-11/compare_retrieval.py). Your lab work is to extend it:

- add at least 3 new questions to `data/sample/eval_questions.json`, each one a real miss you found yourself (Day 1's diagnostic process) — don't add a question that already passes at baseline, since it can't demonstrate improvement;
- run `compare_retrieval.py` with your extended question set and record both hit rates;
- write one sentence per new miss explaining *why* it failed (ticker-vs-name, vocabulary mismatch, or something new you found).

### Required Features

- type hints and a docstring on every function you add, following Week 2 §3.2's comment rules;
- every new eval question is a real, verified miss at baseline — not assumed;
- confirm `pytest` still passes, including `test_retrieve_with_expansion_finds_a_variant_the_original_misses`;
- `LLM_API_KEY`/`LLM_MODEL` are set in your own `.env`, never hard-coded or committed;
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: A Filtering-Only Comparison

Using `hit_rate`, compare basic retrieval against retrieval that always filters to the question's own expected ticker (a "cheating" upper bound, since real usage wouldn't already know the answer). How close does that upper bound get to query expansion's actual measured rate?

## Exercise 2: A Deliberately Bad Rephrasing

Write a stub `generate` that returns an *unhelpful* rephrasing (e.g., a near-identical restatement) and confirm `retrieve_with_expansion` doesn't make hit rate worse than baseline, only potentially better.

## Exercise 3: Fetching a Deeper Pool

Change `retrieve_with_expansion` to fetch more candidates per variant than the final `n_results` (§3.4's limitation) and test whether this recovers any miss the current version doesn't.

## Exercise 4: A Non-Ticker Miss

Find a real retrieval miss that isn't fixable by either metadata filtering or query expansion (hint: think about what Week 8 §4.2 already warned about — high similarity isn't correctness). Document it as a case Week 12's more rigorous evaluation should catch.

## Exercise 5: Git Practice

Make separate commits for your new eval questions, your Exercise 3 pool-size change, and your Exercise 4 write-up.

---

# Common Mistakes

## Building a fix before diagnosing the actual failure

§4.3's point, stated as a mistake: an "improvement" that wasn't built in response to a specific, diagnosed miss is just as likely to help nothing as to help something. Diagnose first (Day 1), fix second (Days 2–3), measure third (Day 4).

## Assuming metadata filtering always helps

§2.2 — filtering requires already knowing the value to filter by. It does nothing for genuine entity ambiguity in the question itself.

## Trusting that filtering finds the *best* passage, not just the right category

§2.3 — filtering to the right ticker doesn't guarantee the single most relevant passage within that ticker's own documents.

## Assuming `retrieve_with_expansion` covers every variant's full ranking

§3.4 — only each variant's own top `n_results` enters the merge pool. A phrasing's second-best match never gets considered unless you fetch deeper.

## Comparing hit rates on a question set that's already trivially easy

If basic retrieval already scores 100%, there's no room to show improvement — Week 11's own question set was deliberately built from real, verified misses (§Day 1), not assumed to be hard.

---

# Interview Preparation

1. Walk through how the MSFT ticker-vs-full-name miss was diagnosed, and how that diagnosis directly shaped the expansion prompt's wording.
2. When does metadata filtering help retrieval, and when can it not help at all?
3. Why does filtering to the correct ticker not guarantee the single best passage?
4. Why is `generate` a keyword-only parameter in `retrieve_with_expansion`?
5. What real limitation does §3.4 describe, and what's one way to address it?
6. Why does this week's hit-rate metric check ticker match rather than exact passage match — what's the trade-off?
7. Why does the lesson insist the improvement numbers (66.7% → 100%) were verified before being written, rather than presented as expected/typical results?
8. What would you need to change to make this week's evaluation catch the kind of miss Exercise 4 asks about?

---

# Week 11 Quiz

## Multiple Choice

1. What actually caused the MSFT retrieval miss diagnosed in §1.2?

   A. A bug in ChromaDB  
   B. The embedding model matched the full company name better than the ticker abbreviation  
   C. Missing metadata  
   D. An API key error

2. When can metadata filtering NOT fix a retrieval miss?

   A. Never — filtering always helps  
   B. When the question doesn't name a specific entity to filter by in the first place  
   C. When there's only one document in the collection  
   D. Filtering never works

3. Why is `generate` keyword-only in `retrieve_with_expansion`?

   A. Python requires it  
   B. So its positional signature matches query_collection's closely enough for retrieval_eval.hit_rate to call either interchangeably  
   C. To make the function slower  
   D. It doesn't need to be keyword-only

4. What does this week's `hit_rate` metric actually check?

   A. Whether the exact best passage was retrieved  
   B. Whether any retrieved chunk's ticker matches the question's expected ticker  
   C. The LLM's confidence score  
   D. Response time

5. What real limitation does §3.4 describe about `retrieve_with_expansion`?

   A. It only calls the LLM once  
   B. It only considers each variant's own top n_results, missing a variant's second-best match  
   C. It doesn't support metadata filtering  
   D. It requires a paid API tier

## Short Answer

6. Explain, in your own words, why diagnosing a miss (Day 1) has to come before building a fix (Days 2–3).

7. Why does filtering guarantee the right ticker but not the right passage?

8. What's the difference between a ticker-vs-full-name miss and a vocabulary-mismatch miss, and which technique fixes which?

9. Why does the lesson provide the exact hand-verified distances (1.0 vs 2.0) behind one of its own test cases?

10. What would you check first if your own measured improvement numbers looked very different from 66.7%/100%?

---

# Week 11 Project Submission Checklist

- [ ] You've diagnosed at least one real retrieval miss and identified its cause (ticker/name mismatch, vocabulary mismatch, or other).
- [ ] `examples/week-11/compare_retrieval.py` runs and prints both hit rates for real.
- [ ] You added at least 3 new eval questions, each a verified real miss at baseline.
- [ ] `pytest` passes, including `test_retrieve_with_expansion_finds_a_variant_the_original_misses`.
- [ ] `LLM_API_KEY`/`LLM_MODEL` are set in your own `.env` (not committed).
- [ ] All work is committed and pushed to GitHub.

---

# Week 11 Reflection

Write 200–300 words answering:

1. What did you build or extend this week?
2. Describe one real retrieval miss you diagnosed yourself, and what you found caused it.
3. What did your own measured hit-rate comparison show?
4. Explain the difference between what metadata filtering can fix and what query expansion can fix.
5. What would you improve about this week's evaluation metric or expansion strategy?

Save as:

```text
week11_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Retrieval error | A case where the retrieved evidence isn't the evidence that actually answers the question |
| Query expansion | Generating alternative phrasings of a query to broaden retrieval coverage |
| Vocabulary mismatch | When a question and its answer use different words for the same idea |
| Hit rate | The fraction of questions where retrieval found evidence matching an expected label |
| Merge and deduplicate | Combining results from multiple retrieval calls without counting the same item twice |

---

# Week Summary

During Week 11, you:

- diagnosed two real retrieval misses against this course's own sample passages, tracing each to a specific, verifiable cause;
- learned when metadata filtering helps retrieval and when it fundamentally can't;
- built and tested `retrieve_with_expansion`, merging results across LLM-generated rephrasings;
- measured basic versus improved retrieval on a real question set — 66.7% to 100%, verified, not assumed;
- learned that a meaningful "improvement" starts with diagnosing a real failure, not building a technique and hoping it helps.

---

# Suggested Reading

## Required

- Gao et al., "Precise Zero-Shot Dense Retrieval without Relevance Labels" — already in this course's [Papers and Reading](../resources/readings.md), the HyDE query-rewriting technique this week's query expansion is a simplified version of

## Recommended

- Liu et al., "Lost in the Middle: How Language Models Use Long Contexts" — already in [Papers and Reading](../resources/readings.md), relevant to §3.4's "how many candidates per variant" trade-off

---

# Next Week

## Week 12: Evaluation

Week 12 introduces:

- building a larger evaluation dataset — at least 15 questions, beyond this week's 6;
- formal retrieval recall and precision, beyond this week's simpler hit-rate metric;
- groundedness and citation checks — confirming an answer's claims are actually supported by its cited evidence (Week 10's `RAGAnswer.citations`, checked rigorously);
- producing an evaluation report and identifying the three largest failure modes.

This week's hit-rate comparison was a first, deliberately simple taste of measurement. Week 12 formalizes it into a real evaluation practice.
