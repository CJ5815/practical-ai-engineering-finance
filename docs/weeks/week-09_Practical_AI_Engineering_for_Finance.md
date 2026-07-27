# Week 9: Vector Databases

**Course:** Practical AI Engineering for Finance  
**Audience:** Senior undergraduate students  
**Schedule:** 1 hour per day, 4 days per week  
**Week Theme:** Storing embeddings persistently and querying them with metadata filters — replacing Week 8's Python list and loop with a real vector database

---

## Week Overview

Week 8 embedded a handful of passages into a Python list and ranked them by hand with a `for` loop. That works for six passages; it doesn't work for a real filing history, where you'd re-embed the same documents every time the script runs and have no way to ask "only search this company's risk factors." A **vector database** solves both problems: it stores embeddings on disk (embed once, query many times) and lets you filter by metadata alongside the similarity search.

This week's code — `src/ai_finance_course/chunking.py` and `src/ai_finance_course/vector_store.py` — is real, committed, tested code, not something you build from a blank file. Read it, understand why it's shaped the way it is, then run [`examples/week-09/build_passage_index.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/examples/week-09/build_passage_index.py) (or the matching notebook) against the same illustrative passages Week 8 used by hand.

**A real bug, left in this lesson on purpose:** building `vector_store.py` for this course turned up a genuine data-loss bug — indexing 8 sample passages produced only 5 stored chunks. §2.3 walks through exactly what happened and how it was fixed, because the failure mode is one you will hit again with real filing data, not just this week's toy example.

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: Documents, Chunks, and Metadata](#day-1-documents-chunks-and-metadata)
- [Day 2: Creating a Collection](#day-2-creating-a-collection)
- [Day 3: Query and Filter](#day-3-query-and-filter)
- [Day 4: Evaluating Chunking Choices](#day-4-evaluating-chunking-choices)
- [Week 9 Coding Lab](#week-9-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 9 Quiz](#week-9-quiz)
- [Week 9 Project Submission Checklist](#week-9-project-submission-checklist)
- [Week 9 Reflection](#week-9-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Next Week](#next-week)

---

# Learning Objectives

By the end of Week 9, you should be able to:

- Split a document into overlapping chunks and attach metadata to each one.
- Create a persistent ChromaDB collection and confirm data survives across separate runs.
- Add documents to a collection with a stable id scheme, and explain why a naive id scheme can silently lose data.
- Query a collection by similarity, with and without a metadata filter.
- Explain the trade-off a chunk size and overlap choice makes, and evaluate it against real query results.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | Documents, chunks, and metadata | Understanding `chunking.py` |
| Day 2 | Create a collection | A persistent collection with real data indexed |
| Day 3 | Query and filter | Filtered and unfiltered query results |
| Day 4 | Evaluate chunking choices | A documented chunk-size comparison |

Each class follows the same session structure as Weeks 1–8: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: Documents, Chunks, and Metadata

## 1.1 Why Split a Document at All

A whole 10-K is too long to embed as one unit — Week 7 §1.2's context window applies to embedding models too, and even without that hard limit, embedding an entire document as a single vector blurs together everything it discusses, from revenue growth to a footnote about a lawsuit. Splitting a document into smaller **chunks** means each one can be embedded and matched on its own, so a query about supplier risk can find exactly the paragraph about suppliers, not the whole filing.

## 1.2 `chunk_text`: Splitting with Overlap

```python
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + chunk_size])
        start += chunk_size - overlap
    return chunks
```

`overlap` matters because a sentence sitting exactly on a chunk boundary would otherwise get cut in half, with neither half containing the whole idea. Repeating the last `overlap` characters of one chunk at the start of the next means a boundary-spanning sentence appears intact in at least one chunk. The `overlap >= chunk_size` check prevents an easy mistake: if overlap ever equals or exceeds chunk_size, `start` never advances and the loop runs forever.

## 1.3 Attaching Metadata: `chunk_document`

```python
def chunk_document(
    text: str, metadata: dict[str, str], chunk_size: int = 500, overlap: int = 50
) -> list[dict]:
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    return [{**metadata, "text": chunk, "chunk_index": i} for i, chunk in enumerate(chunks)]
```

Every chunk carries a copy of the source document's metadata (ticker, document type, filing date — whatever you pass in) plus its own `chunk_index`. This is what makes Day 3's metadata filtering possible later: the vector store doesn't know anything about "AAPL" or "risk factors" on its own, it only knows whatever metadata you attached here.

## Day 1 Activity

Read [`src/ai_finance_course/chunking.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/ai_finance_course/chunking.py) and its tests in full. Run `chunk_text` on a short string with `chunk_size=10, overlap=3` by hand (in a Python shell) and confirm the overlap you see matches what you'd expect from §1.2's explanation.

---

# Day 2: Creating a Collection

## 2.1 A Persistent Client

```python
def get_or_create_collection(
    persist_path: str | Path,
    collection_name: str,
    embedding_function: EmbeddingFunction | None = None,
) -> Collection:
    if embedding_function is None:
        embedding_function = SentenceTransformerEmbeddingFunction()

    client = chromadb.PersistentClient(path=str(persist_path))
    return client.get_or_create_collection(name=collection_name, embedding_function=embedding_function)
```

`chromadb.PersistentClient(path=...)` writes to disk, not memory — reopening the same `persist_path` later gives you back everything you already indexed, without re-embedding a single passage. This was verified directly: index a passage, exit the process, start a fresh Python process pointed at the same path, and the collection's count is unchanged.

## 2.2 The Embedding Function Is Injectable

Notice `embedding_function: EmbeddingFunction | None = None` — the exact same "pass a dependency in, don't hardcode it" pattern as Week 7 §2.2's `generate: Callable[[str], str]`. `get_or_create_collection` defaults to a real `SentenceTransformerEmbeddingFunction` (Week 8's model, wrapped so ChromaDB calls it automatically), but tests pass a small deterministic stub instead — no model download, no multi-second load time, no network:

```python
class KeywordStubEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return [[float(keyword in text.lower()) for keyword in _KEYWORDS] for text in input]
```

Read [`tests/test_vector_store.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/tests/test_vector_store.py) to see this stub used across every test.

## 2.3 A Real Bug: Colliding IDs

The first version of `add_chunks` built each chunk's id from just its metadata:

```python
# The original, buggy version:
ids = [f"{chunk['ticker']}-{chunk['doc_type']}-{chunk['chunk_index']}" for chunk in chunks]
```

Indexing Week 8's 8 sample passages through this produced only **5** stored chunks. Here's why: two different AAPL earnings passages both chunk down to `chunk_index=0`, so both produced the id `"AAPL-earnings-0"` — and `collection.upsert` treats a repeated id as "update this record," not "add a new one." The second passage silently overwrote the first. The same thing happened to three separate macro passages sharing `"MACRO-macro-0"`.

This is not a toy-data quirk. Index a real company's SEC filings and you will have dozens of separate "risk factors" paragraphs sharing the same ticker and doc_type — exactly the condition that triggers this bug.

The fix hashes the chunk's own text into the id:

```python
def _chunk_id(chunk: dict) -> str:
    text_hash = hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest()[:12]
    ticker = chunk.get("ticker", "doc")
    doc_type = chunk.get("doc_type", "na")
    chunk_index = chunk.get("chunk_index", 0)
    return f"{ticker}-{doc_type}-{chunk_index}-{text_hash}"
```

Different text now always produces a different id, even with identical metadata — while re-indexing the *exact same* chunk still produces the *exact same* id, so re-running your indexing script stays idempotent (upserts in place) instead of either losing data or creating duplicates. `test_add_chunks_does_not_collide_when_metadata_matches_but_text_differs` in the test file is the regression test written directly from this failure.

## Day 2 Activity

Run [`examples/week-09/build_passage_index.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/examples/week-09/build_passage_index.py) for real. Confirm it prints "Indexed 8 chunks from 8 passages" — if you see a smaller number, you've reintroduced §2.3's bug.

---

# Day 3: Query and Filter

## 3.1 Querying by Similarity

```python
def query_collection(
    collection: Collection, query: str, n_results: int = 3, where: dict | None = None
) -> list[dict]:
    results = collection.query(query_texts=[query], n_results=n_results, where=where)
    return [
        {"text": doc, "metadata": metadata, "distance": distance}
        for doc, metadata, distance in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        )
    ]
```

`collection.query` embeds the query text automatically (using the same embedding function the collection was created with) and returns the closest matches — the exact same idea as Week 8's `rank_by_similarity`, just computed by ChromaDB instead of a Python loop.

## 3.2 Filtering by Metadata

```python
results = query_collection(collection, "did the company beat earnings expectations?", where={"ticker": "AAPL"})
```

`where={"ticker": "AAPL"}` restricts the similarity search to chunks whose metadata matches — this is the piece Week 8 explicitly couldn't do with a plain Python list. Running the sample passages through both a filtered and unfiltered query shows the difference directly: without a filter, a macro passage about inflation can outrank an on-topic AAPL passage; with the filter, only AAPL chunks are considered at all.

## 3.3 Reading the Distance

Lower `distance` means more similar — the ranking direction is the same idea as Week 8's cosine similarity, just not necessarily the identical formula (ChromaDB's exact distance metric is an implementation detail of the collection's configuration). Don't compare raw distance values across different embedding models or different collections; only compare them *within* one query's own results.

## Day 3 Activity

Run a query against the sample passages both with and without `where={"ticker": "AAPL"}`. Find one case where the top unfiltered result is *not* about the company you actually care about, and explain why the filter fixes it.

---

# Day 4: Evaluating Chunking Choices

## 4.1 What Chunk Size Trades Off

A small `chunk_size` gives precise, focused chunks — good for pinpointing exactly which sentence answers a query — but risks splitting a single idea across two chunks even with overlap, and creates many more chunks to store and search. A large `chunk_size` keeps more context together in one chunk, but a query might match a chunk where only one sentence out of many is actually relevant, and that irrelevant surrounding text becomes noise for whatever reads the chunk next (Week 10's grounded prompt).

## 4.2 Comparing Chunk Sizes on the Same Data

There's no universal "correct" chunk size — the right choice depends on your documents and your queries. Test it directly: index the same passages with two different `chunk_size` values (into two different collection names, so they don't collide) and run the same query against both.

```python
small_collection = get_or_create_collection(PERSIST_PATH, "passages_small_chunks")
large_collection = get_or_create_collection(PERSIST_PATH, "passages_large_chunks")
# index the same passages into each, with chunk_size=100 and chunk_size=1000 respectively
# then compare query_collection results side by side
```

Week 9's own sample passages are all shorter than even a 500-character chunk, so this comparison won't show a difference on the sample data alone — this is exactly why Exercise 2 asks you to test it on a longer, real document instead.

## 4.3 Evidence, Not a Guess

Document which chunk size you chose and why, the same habit Week 6 §4.3 introduced for prompts: "chunk_size=500 because filing sentences rarely exceed a few hundred characters, and testing with a real 10-K risk-factors section showed 1000-character chunks pulling in two unrelated risks per chunk." A specific, tested reason is worth far more than a default left unexamined.

## Day 4 Activity

Take one real, longer piece of text (a paragraph from a real 10-K works well) and index it at two different chunk sizes. Query both and write one sentence on which chunk size produced a more useful top result, and why.

---

# Week 9 Coding Lab

## Extending the Passage Index

This week's core code already exists and is tested — [`src/ai_finance_course/chunking.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/ai_finance_course/chunking.py), [`src/ai_finance_course/vector_store.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/ai_finance_course/vector_store.py), and [`examples/week-09/build_passage_index.py`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/examples/week-09/build_passage_index.py). Your lab work is to extend it:

- add at least two new passages of your own to `data/sample/passages.json`, with a ticker and doc_type that don't collide with existing entries in a way that would trigger §2.3's bug (or, better, deliberately reuse an existing ticker/doc_type pair and confirm the fix handles it correctly);
- write at least one new query and confirm the ranking makes sense, with and without a metadata filter;
- run the chunk-size comparison from §4.2 on a real, longer piece of text and document your conclusion.

### Required Features

- type hints and a docstring on every function you add, following Week 2 §3.2's comment rules;
- any new indexing code reuses `chunk_document`/`add_chunks`/`query_collection` rather than calling ChromaDB directly;
- confirm `pytest` still passes, including `test_add_chunks_does_not_collide_when_metadata_matches_but_text_differs`;
- no API keys needed or committed — this week runs entirely locally, same as Week 8;
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: Break the Fix on Purpose

Temporarily revert `_chunk_id` to the buggy metadata-only version (§2.3) and re-run `build_passage_index.py`. Confirm you see fewer than 8 chunks indexed, then restore the fix and confirm it's back to 8. This is the fastest way to actually believe a fix works, rather than trusting the explanation.

## Exercise 2: A Real Long Document

Find a real 10-K's "Item 1A Risk Factors" section (or any long, real piece of financial text) and run §4.2's chunk-size comparison against it for real. Unlike the short sample passages, this should show an actual, visible difference between chunk sizes.

## Exercise 3: A Third Metadata Field

Add a `filing_date` field to the sample passages' metadata and write a query that filters on `ticker` alone, `filing_date` alone, and both together.

## Exercise 4: Measuring the Idempotency Guarantee

Write a test that indexes the same chunk three times in a row and confirms the collection's count never exceeds 1 — a stronger version of the existing `test_add_chunks_upserts_instead_of_duplicating`.

## Exercise 5: Git Practice

Make separate commits for your new sample passages, your chunk-size comparison, and any new tests.

---

# Common Mistakes

## Building an id from metadata alone

§2.3's bug, exactly: two different documents that happen to share the same ticker and doc_type will silently overwrite each other unless the id also depends on the chunk's actual content.

## Setting overlap close to or above chunk_size

`chunk_text` raises `ValueError` specifically to prevent this — without the check, the loop would never advance and would run forever.

## Comparing distance values across different collections or models

A distance of `0.9` from one collection and `0.9` from a different collection (different embedding model, different data) aren't necessarily comparable. Only compare distances *within* the same query's results.

## Assuming a bigger chunk_size is always safer

A larger chunk keeps more context together, but also pulls in more irrelevant text alongside whatever's actually relevant — there's no free lunch, only a trade-off to test (§4.1–4.2).

## Forgetting this week still needs `pip install -e ".[rag]"`

Same as Week 8 — `chromadb` and `sentence-transformers` aren't base dependencies.

---

# Interview Preparation

1. Why does `chunk_text` need an `overlap`, and what would break without one?
2. Walk through exactly how the id-collision bug (§2.3) happened, and why hashing the text fixes it without breaking idempotent re-indexing.
3. Why is `embedding_function` an injectable parameter on `get_or_create_collection` instead of always constructing a real model internally?
4. What's the practical difference between `chromadb.Client()` and `chromadb.PersistentClient(path=...)`?
5. Why can't you compare `distance` values across two different collections?
6. What trade-off does a larger `chunk_size` make, and how would you actually test which size is better for your data?
7. Why does `add_chunks` use `collection.upsert` instead of `collection.add`?
8. How would you extend this week's metadata filtering to support a date range instead of an exact match?

---

# Week 9 Quiz

## Multiple Choice

1. What problem does chunk overlap solve?

   A. It makes chunking faster  
   B. It prevents a sentence spanning a chunk boundary from being lost entirely  
   C. It reduces the number of chunks produced  
   D. It's required by ChromaDB

2. What actually caused Week 9's real id-collision bug?

   A. ChromaDB has a bug  
   B. Two different chunks produced the same id because it was built from metadata alone, and `upsert` overwrote the first with the second  
   C. The embedding model returned the same vector for different text  
   D. `chunk_text` raised an error

3. Why does `get_or_create_collection` accept an injectable `embedding_function`?

   A. So it can be tested with a fast stub instead of loading a real model  
   B. ChromaDB requires it to be a parameter  
   C. To make the code slower  
   D. It doesn't need to be injectable

4. What's the difference between `chromadb.Client()` and `chromadb.PersistentClient(path=...)`?

   A. There is no difference  
   B. `Client()` is in-memory only; `PersistentClient` writes to disk and survives across separate runs  
   C. `PersistentClient` is slower but otherwise identical  
   D. `Client()` requires an API key

5. What does `where={"ticker": "AAPL"}` do in `query_collection`?

   A. Sorts results by ticker  
   B. Restricts the similarity search to chunks whose metadata matches the filter  
   C. Changes the embedding model used  
   D. Deletes non-matching chunks

## Short Answer

6. Explain, in your own words, why "two documents share the same ticker and doc_type" is a realistic scenario with real SEC filings, not just sample data.

7. Why does hashing the chunk's text (rather than using a random id) keep re-indexing idempotent?

8. What's one concrete downside of choosing too small a `chunk_size`, and one concrete downside of choosing too large a one?

9. Why is comparing chunk sizes on Week 9's own sample passages not a meaningful test, per §4.2?

10. What would you need to change in `vector_store.py` to filter on a numeric range (e.g. "filings after 2024") instead of an exact metadata match?

---

# Week 9 Project Submission Checklist

- [ ] You've read `chunking.py` and `vector_store.py` in full and can explain §2.3's bug in your own words.
- [ ] `examples/week-09/build_passage_index.py` runs and indexes all 8 sample passages (not fewer).
- [ ] You added at least two new passages and at least one new query.
- [ ] You ran the chunk-size comparison (§4.2) on a real, longer document and documented your conclusion.
- [ ] `pytest` passes, including `test_add_chunks_does_not_collide_when_metadata_matches_but_text_differs`.
- [ ] No API key or `.env` file was needed or committed this week.
- [ ] All work is committed and pushed to GitHub.

---

# Week 9 Reflection

Write 200–300 words answering:

1. What did you build or extend this week?
2. Explain the id-collision bug in your own words — what caused it, and why does hashing the text fix it?
3. What did your chunk-size comparison show, and what would you choose for a real 10-K's risk-factors section?
4. Why does `embedding_function` being injectable matter for testing?
5. What would you improve about this week's metadata filtering?

Save as:

```text
week9_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Chunk | A smaller piece of a document, split for embedding and retrieval |
| Overlap | Characters repeated between consecutive chunks, to avoid splitting an idea |
| Vector database | A database that stores embeddings persistently and supports similarity search |
| Metadata filter | Restricting a similarity search to records matching specific field values |
| Upsert | Insert a record, or update it in place if its id already exists |
| Idempotent | Running the same operation twice produces the same result as running it once |

---

# Week Summary

During Week 9, you:

- learned why documents get split into overlapping chunks with attached metadata before embedding;
- created a persistent ChromaDB collection and confirmed data survives across separate runs;
- traced a real data-loss bug (colliding ids from metadata-only id generation) to its root cause and understood the fix;
- queried a collection by similarity, both with and without a metadata filter;
- evaluated a chunk-size choice against real query results instead of assuming a default is correct.

---

# Suggested Reading

## Required

- ChromaDB documentation, "Getting Started"
- ChromaDB documentation, "Embedding Functions"

## Recommended

- ChromaDB documentation, "Filtering" (the `where` clause used in §3.2)

---

# Next Week

## Week 10: Basic RAG

Week 10 introduces:

- RAG architecture — combining this week's retrieval with Weeks 6–7's prompting and validation;
- retrieving context for a real question using `query_collection`;
- constructing a grounded prompt (Week 6's EVIDENCE section, built from retrieved chunks instead of hand-written text);
- returning answers with sources, so every claim traces back to a specific retrieved chunk.

Everything you built this week — chunk, index, query, filter — becomes the retrieval half of a full question-answering pipeline next week.
