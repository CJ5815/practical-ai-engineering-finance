# Week 8: Embeddings

**Course:** Practical AI Engineering for Finance  
**Audience:** Senior undergraduate students  
**Schedule:** 1 hour per day, 4 days per week  
**Week Theme:** Representing text as vectors so "similar meaning" becomes "close together" — and computing that closeness yourself, by hand, before a vector database does it for you

---

## Week Overview

Weeks 6–7 were about *asking* an LLM to reason over text you already handed it. This week is about a different problem: finding the right text to hand it in the first place. Two finance sentences can share zero words and still mean nearly the same thing ("earnings beat expectations" vs. "quarterly results exceeded forecasts") — keyword matching can't see that, but an **embedding** can. This week you'll generate real embeddings, compute similarity between them by hand, and rank passages by relevance to a question. Week 9 then takes exactly this logic and hands it to a real vector database instead of a Python loop.

**A deliberate contrast worth noticing:** Weeks 6–7 cost money per call and needed `LLM_API_KEY`. Embeddings this week run on your own machine via `sentence-transformers` — no API key, no per-call cost, just a one-time model download the first time you run it.

**Setup, before Day 1:** this week's library isn't installed by default. Run:

```bash
pip install -e ".[rag]"
```

**If you're on an Intel Mac:** check your Python version first — `python --version`. PyTorch (which `sentence-transformers` depends on) stopped publishing Intel-macOS builds after version 2.2.2, and that release has no Python 3.13 build at all. If your `.venv` was created with Python 3.13, `pip install -e ".[rag]"` will fail with a dependency resolution error, or in some cases install successfully but crash on import. The fix: create a separate `.venv` for this and the following weeks using Python 3.11 or 3.12 instead (`python3.11 -m venv .venv`), then reinstall (`pip install -e ".[dev,docs,rag]"`). This course's own `pyproject.toml` pins `sentence-transformers`, `transformers`, `torch`, and `numpy` to a combination verified to work together on Python 3.11 — Apple Silicon, Linux, and Windows users are unaffected and can ignore this note.

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: Embedding Intuition](#day-1-embedding-intuition)
- [Day 2: Generating Real Embeddings](#day-2-generating-real-embeddings)
- [Day 3: Cosine Similarity](#day-3-cosine-similarity)
- [Day 4: Testing Finance-Related Queries](#day-4-testing-finance-related-queries)
- [Week 8 Coding Lab](#week-8-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 8 Quiz](#week-8-quiz)
- [Week 8 Project Submission Checklist](#week-8-project-submission-checklist)
- [Week 8 Reflection](#week-8-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Next Week](#next-week)

---

# Learning Objectives

By the end of Week 8, you should be able to:

- Explain what an embedding is and why semantic similarity becomes geometric closeness.
- Generate real sentence embeddings locally with `sentence-transformers`, with no API key required.
- Explain why cosine similarity, not raw distance, is the standard metric for comparing text embeddings.
- Implement cosine similarity by hand with `numpy`.
- Rank a set of passages by relevance to a query.
- Identify a case where high similarity doesn't mean "correct" or "current" — a limitation this course revisits during evaluation (Week 12).

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | Embedding intuition | A short written explanation, no code required yet |
| Day 2 | Generate or load embeddings | Real embeddings for a handful of finance passages |
| Day 3 | Cosine similarity | A hand-written `cosine_similarity` function |
| Day 4 | Test finance-related queries | A ranked list of passages for a real question |

Each class follows the same session structure as Weeks 1–7: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: Embedding Intuition

## 1.1 From Words to Vectors

An **embedding** is a list of numbers (a vector) that represents a piece of text's *meaning* — not its exact wording. Two sentences with almost no words in common can still produce nearly identical embeddings, if what they're saying is the same thing:

```text
"Apple's revenue grew 8% year over year."
"Apple's quarterly sales increased eight percent."
```

Different words, same claim — a well-trained embedding model places these two close together in vector space, while placing an unrelated sentence ("The Federal Reserve raised interest rates") far away.

## 1.2 Why This Matters for Finance Text

Keyword search fails constantly in finance writing, because the same idea gets phrased a dozen different ways across filings, transcripts, and analyst notes: "beat expectations," "exceeded forecasts," "outperformed consensus" are all the same claim in different words. An embedding-based search finds all three for a query like "did the company beat estimates," where keyword search would only find the exact phrase you typed.

## 1.3 What You're Not Doing This Week

You are not fine-tuning a model, and you are not yet storing embeddings anywhere persistent — that's Week 9's job, once you understand what's being stored and why. This week, embeddings live in a Python list for the length of one script.

## Day 1 Activity

Without writing code, list three pairs of finance-related sentences that mean the same thing but share almost no words (like §1.1's example). For each pair, note one sentence that means something *different* despite sharing several words with one of them (a "false friend" for keyword search).

---

# Day 2: Generating Real Embeddings

## 2.1 Loading a Real Model

`sentence-transformers` runs a real embedding model locally — the first call downloads model weights (a few hundred megabytes, one-time, requires network); every call after that runs entirely offline:

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
```

`all-MiniLM-L6-v2` is a small, fast, widely used sentence-embedding model — a reasonable default for coursework where speed matters more than squeezing out the last bit of accuracy.

## 2.2 Embedding a Batch of Passages

```python
passages = [
    "Apple's revenue grew 8% year over year, driven by strong iPhone sales.",
    "The Federal Reserve raised interest rates by 25 basis points.",
    "Quarterly earnings exceeded analyst expectations across most segments.",
]

embeddings = model.encode(passages)
print(embeddings.shape)  # (3, 384) — 3 passages, 384 numbers each
```

Each passage becomes a 384-number vector. That number (the **embedding dimension**) is fixed by the model you chose — every passage you ever embed with `all-MiniLM-L6-v2` produces the same-length vector, which is exactly what makes comparing them meaningful.

## 2.3 One Model, Reused

Loading `SentenceTransformer(...)` is the slow, one-time part — always load it once and reuse it for every `.encode(...)` call, rather than constructing a new model instance per passage. This is the same "set up once, reuse many times" instinct as Week 5's `EdgarClient` — just applied to a local model instead of a network client.

## Day 2 Activity

Embed your own three sentence pairs from Day 1's activity. Print each embedding's shape to confirm it matches what §2.2 showed, and note that the same-meaning pairs are ready to compare — you just don't have a similarity number for them yet.

---

# Day 3: Cosine Similarity

## 3.1 Why Not Just Raw Distance?

Two embeddings can point in almost exactly the same direction but have different magnitudes (roughly, different "lengths") for reasons unrelated to meaning — a longer passage might produce a larger-magnitude vector than a short one saying the same thing. **Cosine similarity** measures the *angle* between two vectors, not their raw distance, which is why it's the standard metric for comparing text embeddings: same direction (same meaning) scores high, regardless of magnitude.

## 3.2 Computing It By Hand

```python
import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors, from -1 (opposite) to 1 (identical direction)."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
```

`np.dot(a, b)` is the raw dot product; dividing by both vectors' norms (lengths) is exactly what removes magnitude from the answer, leaving only direction. In practice, semantically similar finance sentences typically score above roughly `0.5`, while unrelated ones often land near `0` — treat these as rough intuition, not a hard universal threshold.

## 3.3 Ranking Passages Against a Query

```python
def rank_by_similarity(
    query: str, passages: list[str], model: SentenceTransformer
) -> list[tuple[str, float]]:
    """Rank passages by similarity to a query, most similar first."""
    query_embedding = model.encode(query)
    passage_embeddings = model.encode(passages)
    scored = [
        (passage, cosine_similarity(query_embedding, embedding))
        for passage, embedding in zip(passages, passage_embeddings)
    ]
    return sorted(scored, key=lambda item: item[1], reverse=True)
```

This is the entire core idea behind retrieval: embed a question, embed your candidate passages once, and rank by cosine similarity. Week 9 replaces the Python list and loop here with a vector database that does the same ranking far faster at scale — the underlying math doesn't change.

## Day 3 Activity

Run `rank_by_similarity` with the query `"did the company's results beat expectations?"` against §2.2's three passages. Confirm the earnings-related passage ranks above the interest-rate one, and explain in one sentence why cosine similarity, not word overlap, is what put it there.

---

# Day 4: Testing Finance-Related Queries

## 4.1 Does the Ranking Make Sense?

Testing an embedding-based ranking isn't like testing `simple_return` (Week 1) — there's no single exact expected output. The practical check is qualitative but still rigorous: for a query with an obviously relevant passage in your set, does that passage rank at or near the top, consistently, across several related phrasings of the same query?

## 4.2 A Real Limitation: Similar Isn't the Same as Correct

High cosine similarity means "discusses a similar topic in a similar way" — it says nothing about whether a passage is factually accurate, current, or even about the same company. A passage about a competitor's earnings can rank highly similar to a query about your target company, simply because both discuss "quarterly earnings" in similar language. This is a real, load-bearing limitation, not an edge case — Week 12 (Evaluation) comes back to exactly this gap, since it's one of the most common ways a retrieval-based system quietly returns something wrong-but-plausible-sounding.

## 4.3 Where This Goes Next

Everything this week ran in a Python list, recomputing every embedding on every run. Week 9 stores embeddings persistently in a real vector database (so you embed once, query many times), and adds metadata filtering (e.g., "only search this company's filings"). Weeks 10–11 then combine that retrieval step with Weeks 6–7's prompting and validation into a full retrieval-augmented generation (RAG) pipeline.

## Day 4 Activity

Write three different phrasings of the same underlying question (e.g., "did revenue grow," "was the quarter strong," "how did sales perform") and confirm they all rank the same passage highest. Then construct one deliberately misleading passage — about a different company's earnings, phrased similarly — and confirm §4.2's limitation for yourself: does it rank higher than you'd want?

---

# Week 8 Coding Lab

## Ranking Financial Passages by Similarity

Create `examples/week-08/rank_passages.py`:

- `cosine_similarity(a: np.ndarray, b: np.ndarray) -> float` (§3.2).
- `rank_by_similarity(query: str, passages: list[str], model: SentenceTransformer) -> list[tuple[str, float]]` (§3.3).
- A small set of at least six realistic finance passages (earnings, risk factors, macro commentary — mix topics deliberately) and at least three test queries, each printing the ranked results.

### Required Features

- type hints and a docstring on every function, following Week 2 §3.2's comment rules;
- the `SentenceTransformer` model is loaded exactly once and reused, not reconstructed per call (§2.3);
- at least one test confirms `cosine_similarity` returns `1.0` (within floating-point tolerance) for a vector compared to itself;
- at least one test confirms `rank_by_similarity` puts an obviously relevant passage above an obviously unrelated one;
- no API keys, tokens, or `.env` files needed or committed — this week runs entirely locally;
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: Self-Similarity Sanity Check

Confirm `cosine_similarity(embedding, embedding)` (a vector compared to itself) returns very close to `1.0`. Explain why that must always be true, regardless of which passage you chose.

## Exercise 2: An Orthogonal Pair

Find (or construct) two passages whose cosine similarity is close to `0`. What does a near-zero score mean here, versus a negative score?

## Exercise 3: Sensitivity to Phrasing

Take one query and rewrite it five different ways (formal, casual, a question, a statement, using a synonym for a key term). Does the top-ranked passage stay stable across all five?

## Exercise 4: The Misleading-Passage Exercise, Formalized

Turn Day 4's misleading-passage check into an actual test: assert that a passage about the *wrong* company doesn't outrank a passage about the *right* company for a company-specific query. If it does, that's a real, documented limitation worth writing down (Week 6 §4.3's habit).

## Exercise 5: Git Practice

Make separate commits for `cosine_similarity`/its tests and `rank_by_similarity`/its tests.

---

# Common Mistakes

## Reconstructing the model on every call

`SentenceTransformer("all-MiniLM-L6-v2")` is the expensive part — call it once, reuse the `model` object, exactly like Week 5's client-reuse pattern (§2.3).

## Comparing embeddings from two different models

A `sentence-transformers` embedding and, say, an OpenAI embedding are not comparable to each other — different models produce different vector spaces with no shared meaning between coordinates. Always embed everything you're comparing with the same model.

## Treating cosine similarity as a universal fixed threshold

"Above 0.5 means relevant" is a rough intuition (§3.2), not a guarantee — the right threshold depends on your specific passages and model. Validate against your own data rather than hard-coding someone else's number.

## Assuming high similarity means factually correct

§4.2's limitation, restated: a highly similar passage can still be about the wrong company, the wrong quarter, or simply wrong. Retrieval finds *relevant-sounding* text, not *verified* text.

## Forgetting `pip install -e ".[rag]"`

`sentence-transformers` isn't a base dependency — without the `[rag]` extra, `from sentence_transformers import SentenceTransformer` raises `ModuleNotFoundError` before you've written a single line of your own code.

---

# Interview Preparation

1. What does an embedding represent, and why can two sentences with no shared words still have similar embeddings?
2. Why is cosine similarity preferred over raw Euclidean distance for comparing text embeddings?
3. Why must you always use the same embedding model for both sides of a comparison?
4. Give a concrete example where high cosine similarity would mislead someone into trusting a wrong answer.
5. Why is loading `SentenceTransformer(...)` once, outside a loop, important for performance?
6. What's the difference between what you built this week and what a vector database (Week 9) provides?
7. How would you test an embedding-based ranking function, given there's no single "correct" numeric output?
8. Why does this week need no `LLM_API_KEY`, unlike Weeks 6–7?

---

# Week 8 Quiz

## Multiple Choice

1. What does an embedding represent?

   A. The exact words in a sentence  
   B. A vector representing a piece of text's meaning  
   C. A compressed version of the original text that can be decompressed exactly  
   D. A count of how many times each word appears

2. Why is cosine similarity preferred over raw distance for text embeddings?

   A. It's faster to compute  
   B. It measures direction (meaning) rather than magnitude, which can vary for unrelated reasons  
   C. It always returns a value between 0 and 100  
   D. Raw distance doesn't exist for vectors

3. What happens if you compare an embedding from one model to an embedding from a different model?

   A. It works fine, since all embeddings are the same format  
   B. The comparison is meaningless — different models produce different, incompatible vector spaces  
   C. It automatically converts between them  
   D. It raises an error immediately

4. What is the main limitation of similarity-based ranking, per §4.2?

   A. It's too slow for real use  
   B. High similarity means "similar topic/phrasing," not "factually correct or current"  
   C. It only works for English text  
   D. It requires an API key

5. What does `SentenceTransformer("all-MiniLM-L6-v2").encode(passages)` return?

   A. A single similarity score  
   B. A list of the input passages, unchanged  
   C. A vector (fixed-length list of numbers) for each passage  
   D. A ranked list of passages

## Short Answer

6. Explain, in your own words, why keyword search and embedding-based search can disagree on the same query.

7. Why does this week's `cosine_similarity` divide by both vectors' norms instead of just returning the raw dot product?

8. What would you need to change if you wanted to compare embeddings from two different models?

9. Why does Week 9 replace this week's Python list with a real vector database, rather than just running the same loop at a larger scale?

10. Construct one example (in words) where a passage would rank highly similar to a query but be the *wrong* answer to give someone.

---

# Week 8 Project Submission Checklist

- [ ] `examples/week-08/rank_passages.py` has `cosine_similarity` and `rank_by_similarity`.
- [ ] The `SentenceTransformer` model is loaded once and reused, not reconstructed per call.
- [ ] At least six realistic, topically varied finance passages are included.
- [ ] At least one test confirms self-similarity is close to `1.0`.
- [ ] At least one test confirms an obviously relevant passage outranks an obviously unrelated one.
- [ ] You constructed and documented at least one "misleading passage" case (§4.2/Exercise 4).
- [ ] No API key or `.env` file was needed or committed this week.
- [ ] All work is committed and pushed to GitHub.

---

# Week 8 Reflection

Write 200–300 words answering:

1. What did you build this week?
2. Why does cosine similarity, not raw distance, make sense for comparing text embeddings?
3. What surprised you most when testing your own queries against your passages?
4. Describe a case where similarity ranking gave you a "similar but wrong" result. How would you catch this in a real system?
5. What would you improve about your passage set or query set?

Save as:

```text
week8_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Embedding | A vector representation of text capturing meaning, not exact wording |
| Embedding dimension | The fixed length of every vector a given model produces |
| Cosine similarity | A similarity measure based on the angle between two vectors, ignoring magnitude |
| Vector space | The set of all possible embedding vectors a model can produce |
| Semantic search | Finding relevant text by meaning rather than exact keyword match |

---

# Week Summary

During Week 8, you:

- learned what an embedding is and why semantic similarity becomes geometric closeness;
- generated real sentence embeddings locally with `sentence-transformers`, at no per-call cost;
- implemented cosine similarity by hand with `numpy` and understood why it beats raw distance for this purpose;
- ranked finance passages by relevance to a query, and tested that ranking against multiple phrasings;
- identified a real limitation — high similarity doesn't guarantee correctness — that this course returns to during evaluation (Week 12).

---

# Suggested Reading

## Required

- Reimers and Gurevych, "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks" — already in this course's [Papers and Reading](../resources/readings.md), and the model family `sentence-transformers` is built from
- `sentence-transformers` documentation, "Quickstart"

## Recommended

- `numpy` documentation, "Linear algebra" (`numpy.dot`, `numpy.linalg.norm`)

---

# Next Week

## Week 9: Vector Databases

Week 9 introduces:

- documents, chunks, and metadata — how a real corpus gets prepared for retrieval;
- creating a vector database collection and indexing your embeddings persistently, instead of recomputing them in a Python list every run;
- querying with metadata filters (e.g., restricting a search to one company's filings);
- evaluating chunking choices — how you split a long document affects what gets retrieved.

Everything you tested by hand this week — embed, compare, rank — becomes a single query call to a real vector database next week.
