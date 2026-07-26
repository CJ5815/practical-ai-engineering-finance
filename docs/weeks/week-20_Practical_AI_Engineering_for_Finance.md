# Week 20: Knowledge Graphs from SEC Filings with Claude

**Course:** Practical AI Engineering for Finance  
**Audience:** Senior undergraduate students  
**Schedule:** 1 hour per day, 4 days (this week only — an optional, advanced extension)  
**Week Theme:** Using Claude to extract structured entities and relationships from unstructured filing text, and representing them as a queryable, visualizable knowledge graph

---

## Week Overview

Week 18 built `sec_thesis`'s foundation: a caching SEC client, CIK resolution, and a DuckDB filing index. That package's own `CLAUDE.md` listed `filing_parser.py`, `llm/`, and `analysis/` as "not yet built... candidates for later phases" — and added the `beautifulsoup4`/`lxml` dependencies for HTML parsing that Phase 1 never actually used. Week 20 is that next phase.

A 10-K's "Item 1. Business" and "Competition" sections are full of relationships a human analyst reads instinctively: "we compete with Samsung and Qualcomm," "Tim Cook, Chief Executive Officer," "the Company's subsidiaries." This week uses Claude to pull those relationships out as structured data, then represents them as a **knowledge graph** — nodes are companies and people, edges are typed, evidenced relationships between them.

**A real architecture decision, worth understanding rather than skimming past:** the graph library is **NetworkX**, not a graph database like Neo4j. NetworkX is pure Python, in-memory, and needs zero infrastructure — no server or Docker container for students to run. It draws directly with matplotlib (already a course dependency) and serializes to plain JSON. This is the same "no unnecessary infra" bias that chose DuckDB over Postgres in Week 18. A production system with millions of entities would eventually outgrow this and move to a real graph database — that trade-off belongs in [Where to Go From Here](#where-to-go-from-here), not this week's build.

**LLM calling stays consistent with Week 17:** entity/relationship extraction uses the same injected `generate: Callable[[str], str]` pattern as `value_investor.py` — provider-agnostic, testable with a stub, no API key needed in tests. Exactly one function (`_call_llm` in the CLI, `call_llm` in the example) is Anthropic-specific.

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: What a Knowledge Graph Is](#day-1-what-a-knowledge-graph-is)
- [Day 2: Extracting Entities and Relationships with Claude](#day-2-extracting-entities-and-relationships-with-claude)
- [Day 3: Building and Querying the Graph](#day-3-building-and-querying-the-graph)
- [Day 4: Visualization, Persistence, and the CLI](#day-4-visualization-persistence-and-the-cli)
- [Week 20 Coding Lab](#week-20-coding-lab)
- [Practice Exercises](#practice-exercises)
- [Common Mistakes](#common-mistakes)
- [Interview Preparation](#interview-preparation)
- [Week 20 Quiz](#week-20-quiz)
- [Week 20 Project Submission Checklist](#week-20-project-submission-checklist)
- [Week 20 Reflection](#week-20-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [Suggested Reading](#suggested-reading)
- [Where to Go From Here](#where-to-go-from-here)

---

# Learning Objectives

By the end of Week 20, you should be able to:

- Explain why company relationship data fits a graph model better than a flat table.
- Justify choosing an in-memory graph library (NetworkX) over a graph database server for a course-scale project.
- Turn a cached filing's raw HTML into clean text suitable for an LLM prompt, including handling inline XBRL metadata.
- Design pydantic schemas that constrain an LLM's output to a fixed, validated shape (`Literal` types for entity/relation kinds).
- Use the injected-callable pattern to keep extraction logic provider-agnostic and testable without an API key.
- Build, query, persist, and visualize a directed graph with NetworkX.
- Wire new commands into an existing Typer CLI, building on prior work rather than starting over.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | What a knowledge graph is | Design notes, library choice |
| Day 2 | Extracting entities/relationships with Claude | `filing_parser.py`, `llm/extraction.py` |
| Day 3 | Building and querying the graph | `graph.py` (build + query) |
| Day 4 | Visualization, persistence, CLI | `graph.py` (save/load/visualize), `cli.py` additions |

Each session follows the same structure as prior weeks: review and setup, new concept, guided practice, testing, and committing the work.

---

# Day 1: What a Knowledge Graph Is

## 1.1 Why a Graph, Not a Table

A flat table of "Company A competes with Company B" rows can answer "who competes with Apple?" But it struggles with questions that chain relationships together: "which suppliers does Apple share with its competitors?" or "who are the most connected entities across all of Apple's filings?" A graph makes those chains a first-class operation — traversal and centrality — instead of a series of joins.

Nodes here are entities: companies (`Apple Inc.`, ticker `AAPL`) and people (`Tim Cook`). Edges are directed and typed:

```python
_RELATION_COLORS = {
    "competitor_of": "#d9534f",
    "subsidiary_of": "#5a7bb0",
    "executive_of": "#2a9d3f",
    "supplier_of": "#f0a35a",
}
```

Each edge also carries an `evidence` string — the exact filing snippet that supports it (`CLAUDE.md` rule 4: preserve exact source text for extracted evidence).

## 1.2 Why NetworkX, Not a Graph Database

Neo4j (or a similar graph database) is the industry-standard choice for knowledge graphs at scale — but it requires running a server, which every student would need to install, configure, and keep running for one course exercise. NetworkX is a pure-Python library: `pip install networkx` and you have an in-memory directed graph, with built-in centrality algorithms and matplotlib drawing, no process to manage. For a project scoped to a handful of filings and a few dozen entities, that trade-off clearly favors NetworkX. A graph with millions of nodes and concurrent multi-user access would favor a real graph database — a distinction worth stating plainly rather than glossing over.

## Day 1 Activity

Sketch (on paper or in a markdown file) the knowledge graph you'd expect from a single tech company's "Competition" section: list 3–5 nodes and the relationship type connecting each pair.

---

# Day 2: Extracting Entities and Relationships with Claude

## 2.1 From HTML to Prompt Text

```python
def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style"]):
        tag.decompose()

    # Modern 10-Ks embed inline XBRL: machine-readable tag data sitting in
    # display:none elements (often <ix:header>) that browsers never render
    # but get_text() would otherwise include as if it were filing prose.
    for tag in soup.find_all(style=re.compile(r"display:\s*none")):
        tag.decompose()

    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()
```

This was checked against a real, large filing, not just a synthetic fixture: a real 1.5MB Apple 10-K produced clean, meaningful text, including its actual "Competition" section. The `display:none` step mattered in practice — without it, the first ~20,000 characters of a real inline-XBRL 10-K are hidden tag-name metadata (`AmendmentFlag`, `DocumentFiscalYearFocus`, ...), not filing prose, which would silently starve a length-truncated prompt of any real content.

## 2.2 Schemas That Constrain the LLM's Output

```python
class Entity(BaseModel):
    name: str
    entity_type: Literal["company", "person"]
    ticker: str | None = None


class Relationship(BaseModel):
    source: str
    target: str
    relation_type: Literal["competitor_of", "subsidiary_of", "executive_of", "supplier_of"]
    evidence: str


class ExtractionResult(BaseModel):
    entities: list[Entity]
    relationships: list[Relationship]
```

`Literal` types mean pydantic itself rejects a relationship type the LLM invents that isn't one of the four allowed values — `CLAUDE.md` rule 8 ("all LLM outputs must conform to Pydantic schemas") enforced structurally, not just by asking nicely in the prompt.

## 2.3 The Injected-Callable Pattern, Again

```python
def extract_relationships(ticker: str, filing_text: str, generate: Callable[[str], str]) -> ExtractionResult:
    prompt = build_prompt(ticker, filing_text)
    raw_response = generate(prompt)
    parsed = json.loads(_extract_json(raw_response))
    return ExtractionResult(**parsed)
```

Identical shape to Week 17's `evaluate_company(..., generate: Callable[[str], str])`. Tests pass a stub `generate` that returns canned JSON — no network call, no API key, and the pydantic validation still runs for real. `_extract_json` strips a ` ```json ` code fence if the model wraps its answer in one, the same defensive parsing habit from earlier prompting weeks.

## Day 2 Activity

Write a one-paragraph prompt-engineering note: which constraint in `build_prompt` (§2.2's `CONSTRAINTS` section) do you think matters most for preventing fabricated relationships, and why?

---

# Day 3: Building and Querying the Graph

## 3.1 Assembling the Graph

```python
def build_graph(results: list[ExtractionResult]) -> nx.DiGraph:
    graph = nx.DiGraph()
    for result in results:
        for entity in result.entities:
            graph.add_node(entity.name, entity_type=entity.entity_type, ticker=entity.ticker)
        for rel in result.relationships:
            graph.add_edge(
                rel.source, rel.target,
                relation_type=rel.relation_type, evidence=rel.evidence,
            )
    return graph
```

Taking a `list[ExtractionResult]` (not one) matters: running `extract-relationships` across several cached filings for the same company merges everything into a single graph — mentioning "Samsung" in two different 10-Ks doesn't create two separate nodes.

## 3.2 Query Helpers

```python
def competitors_of(graph: nx.DiGraph, name: str) -> list[str]:
    found = []
    for _, target, data in graph.out_edges(name, data=True):
        if data.get("relation_type") == "competitor_of":
            found.append(target)
    for source, _, data in graph.in_edges(name, data=True):
        if data.get("relation_type") == "competitor_of":
            found.append(source)
    return found


def most_central_entities(graph: nx.DiGraph, top_n: int = 5) -> list[tuple[str, float]]:
    centrality = nx.degree_centrality(graph)
    return sorted(centrality.items(), key=lambda item: item[1], reverse=True)[:top_n]
```

`competitors_of` checks both edge directions deliberately — the LLM might extract "Apple competes with Samsung" as `(Apple, competitor_of, Samsung)` or the reverse, and a competitor relationship is symmetric in meaning even if the edge is directed. `most_central_entities` uses degree centrality — simplest possible ranking of "how many relationships mention this entity" — as a first cut; betweenness or eigenvector centrality would answer a more subtle question, left as an extension.

## 3.3 A Naming Problem Worth Naming

The LLM chooses entity names freely from the filing text — one run might extract `"Apple Inc."`, another `"Apple"`. Code that needs to find "the company this filing is about" should look up the entity by `ticker` (which the prompt asks the LLM to fill in when known), not by assuming an exact name string:

```python
filer = next((e for e in result.entities if e.ticker == TICKER), None)
```

This is a real limitation, not a hypothetical one — it surfaced during this week's own live verification and was fixed the same way shown here.

## Day 3 Activity

Using the sample fixture in `tests/sec_thesis/test_graph.py`, call `most_central_entities` and explain in one sentence why the CEO node ranks lower than the company node.

---

# Day 4: Visualization, Persistence, and the CLI

## 4.1 Saving and Loading

```python
def save_graph(graph: nx.DiGraph, path: str | Path) -> None:
    data = nx.node_link_data(graph, edges="edges")
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_graph(path: str | Path) -> nx.DiGraph:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return nx.node_link_graph(data, edges="edges")
```

Plain JSON, not a binary format — readable, diffable, and version-controllable if you choose to commit a snapshot. The `edges="edges"` argument matters for this NetworkX version; without it, the node-link format defaults differently and round-tripping can silently change the edge key name.

## 4.2 Drawing the Graph

```python
def visualize_graph(graph: nx.DiGraph, path: str | Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 8))
    pos = nx.spring_layout(graph, seed=42)
    edge_colors = [
        _RELATION_COLORS.get(data.get("relation_type"), "#999999")
        for _, _, data in graph.edges(data=True)
    ]
    nx.draw(graph, pos, ax=ax, with_labels=True, edge_color=edge_colors, arrows=True)
    fig.savefig(path)
    plt.close(fig)
```

`seed=42` on the spring layout matters for testability — without it, node positions (and therefore the rendered image) would differ on every run, making "does this produce a sensible-looking image" hard to check reproducibly.

## 4.3 Wiring the CLI

```python
@app.command("extract-relationships")
def extract_relationships_command(ticker: str) -> None:
    settings = load_settings()
    with FilingsDB(settings.duckdb_path) as db:
        filings = [f for f in db.query_by_ticker(ticker.upper()) if f.local_path]
    if not filings:
        console.print(f"No cached filings for {ticker}. Run fetch-filings first.")
        raise typer.Exit(code=1)
    ...
```

`show-graph` fails the same clean way if `extract-relationships` hasn't been run yet — a helpful message and exit code 1, not a stack trace, tested directly (`test_show_graph_fails_cleanly_without_extraction`).

## 4.4 Live Verification

This week's pipeline was checked against a real, large SEC filing, not just test fixtures: a genuine Apple 10-K (1.5MB of HTML) was fetched via Week 18's cached-fetch pipeline, parsed down to ~220,000 characters of clean text (confirmed to include a real "Competition" section after the §2.1 XBRL fix), truncated to the first 15,000 characters for the prompt, and run through the full `extract_relationships` → `build_graph` → `save_graph` → `load_graph` → `visualize_graph` pipeline. No real `LLM_API_KEY` was available in the verification environment, so the actual Claude call was exercised with a realistic stub response rather than a live one — the 29 stub-based unit/integration tests are the primary correctness check for the extraction and graph logic itself. Run this for real with your own API key (`examples/week-20/build_company_graph.py`) to see a live extraction.

## Day 4 Activity

Run `sec-thesis extract-relationships AAPL` and then `sec-thesis show-graph AAPL` for real (requires `LLM_API_KEY`/`LLM_MODEL`/`SEC_USER_AGENT` in `.env`, and `fetch-filings AAPL` run first). Open the saved PNG and describe one relationship you didn't expect the LLM to find.

---

# Week 20 Coding Lab

## sec_thesis Phase 2

Extend [`src/sec_thesis/`](https://github.com/CJ5815/practical-ai-engineering-finance/blob/main/src/sec_thesis) and its tests:

- confirm `filing_parser.py`, `llm/extraction.py`, and `graph.py` all exist and are tested;
- set `LLM_API_KEY`, `LLM_MODEL`, and `SEC_USER_AGENT` in your own `.env` and run `extract-relationships`/`show-graph` for real against a company you already ran `fetch-filings` for in Week 18;
- confirm the saved graph JSON round-trips correctly through `load_graph`;
- confirm `pytest` passes, including the stub-`generate`-based extraction tests.

### Required Features

- type hints and a docstring on every function, following Week 2 §3.2's comment rules;
- extraction logic (`llm/extraction.py`) never imports an LLM SDK or calls the network itself — only the CLI's `_call_llm` does;
- graph construction and querying (`graph.py`) are fully deterministic — no LLM involved (CLAUDE.md rule 6);
- every module has at least one test (CLAUDE.md rule 12);
- no API keys, tokens, or `.env` files committed;
- all work committed and pushed to GitHub.

---

# Practice Exercises

## Exercise 1: A Second Relation Type

Add a `parent_of` relation type (for holding-company structures) to the `Literal` in `Relationship.relation_type`, add a color for it in `_RELATION_COLORS`, and update the prompt's constraints to mention it.

## Exercise 2: Betweenness Centrality

Add a `most_central_entities` variant (or a parameter) that ranks by `nx.betweenness_centrality` instead of degree centrality, and explain in a comment what different question it answers.

## Exercise 3: Multi-Filing Merge

Run `extract-relationships` against two different filings for the same company (e.g. two different years' 10-Ks) and confirm in `graph.py`'s tests that mentioning the same entity twice doesn't create duplicate nodes.

## Exercise 4: A Third Company

Run the full pipeline for a company other than Apple and compare its most-central entities to Apple's.

## Exercise 5: Git Practice

Make commits for `filing_parser.py`, `llm/extraction.py`, and `graph.py`/`cli.py` separately.

---

# Common Mistakes

## Trusting `get_text()` to skip hidden content

BeautifulSoup's `get_text()` has no concept of CSS visibility — a `display:none` XBRL metadata block is just as "visible" to it as the actual filing prose. §2.1's fix (explicitly decomposing `display:none` elements) is necessary, not optional, for real modern 10-Ks.

## Assuming the LLM will always name an entity the same way

§3.3 — look up the filer's own node by `ticker`, not by an assumed exact name string like `"Apple Inc."`.

## Forgetting `edges="edges"` in `node_link_data`/`node_link_graph`

Omitting it changes the default edge-key name in the serialized JSON, which can silently break `load_graph` round-tripping between NetworkX versions.

## Skipping the `seed` in `spring_layout`

Without a fixed seed, the visualization's node positions change every run, making it much harder to reason about whether a rendered graph "looks right."

## Sending the entire filing text to the LLM unmodified

A full 10-K can run past 200,000 characters. `MAX_FILING_TEXT_CHARS` truncates deliberately — a production system would chunk and retrieve relevant sections (Weeks 9–11's RAG techniques) instead of a flat truncation.

---

# Interview Preparation

1. Why does this project use NetworkX instead of a graph database like Neo4j?
2. What does representing `Literal["competitor_of", ...]` in a pydantic model actually enforce, and what does it not enforce?
3. Why does `extract_relationships` take a `generate: Callable[[str], str]` instead of calling an LLM SDK directly?
4. What real problem did the `display:none` XBRL fix solve, and how would you have discovered it without live-testing against a real filing?
5. Why does `competitors_of` check both `in_edges` and `out_edges`?
6. What's the trade-off between degree centrality and betweenness centrality for "most important entity"?
7. Why is a fixed `seed` important for `nx.spring_layout` in a course context?
8. Why does `build_graph` accept a list of extraction results rather than just one?

---

# Week 20 Quiz

## Multiple Choice

1. Why was NetworkX chosen over a graph database server for this project?

   A. NetworkX is faster at scale  
   B. No infrastructure to run — pure Python, in-memory, same reasoning that chose DuckDB over Postgres  
   C. Neo4j doesn't support Python  
   D. NetworkX is required by pydantic

2. What does a `Literal["competitor_of", "subsidiary_of", "executive_of", "supplier_of"]` type annotation do?

   A. Makes the LLM smarter  
   B. Causes pydantic to reject any other value at validation time  
   C. Speeds up the LLM call  
   D. Nothing at runtime

3. Why did `extract_text` need an explicit fix for `display:none` elements?

   A. BeautifulSoup crashes on hidden elements  
   B. Inline XBRL metadata sits in hidden elements that `get_text()` includes anyway, starving a truncated prompt of real content  
   C. XBRL isn't valid HTML  
   D. matplotlib requires it

4. Why does `competitors_of` check both `in_edges` and `out_edges` for a node?

   A. NetworkX requires it  
   B. A competitor relationship is meaningful in either direction even though the edge is stored as directed  
   C. To double the results  
   D. It doesn't need to — this is a bug

5. What does the `edges="edges"` argument to `node_link_data`/`node_link_graph` control?

   A. Node color  
   B. The key name used for the edge list in the serialized JSON  
   C. Whether the graph is directed  
   D. The visualization layout

## Short Answer

6. Explain, in your own words, why entity names extracted by an LLM shouldn't be relied on as stable identifiers.

7. Why is `graph.py` fully deterministic while `llm/extraction.py` is not, and how does that split follow `CLAUDE.md` rule 6/7?

8. What would you need to change to support extracting relationships from an 8-K instead of a 10-K?

9. Why does `MAX_FILING_TEXT_CHARS` exist, and what's the more scalable long-term alternative?

10. Name one thing that would need to change if this project's entity count grew from dozens to millions.

---

# Week 20 Project Submission Checklist

- [ ] `src/sec_thesis/` has `filing_parser.py`, `llm/extraction.py`, `graph.py`, and updated `cli.py`.
- [ ] Every function has a docstring and type hints.
- [ ] Every new module has at least one test file under `tests/sec_thesis/`.
- [ ] `pytest` passes, including stub-`generate`-based extraction tests.
- [ ] `extract-relationships` and `show-graph` both work against a real cached filing.
- [ ] The saved graph JSON round-trips correctly through `load_graph`.
- [ ] `src/sec_thesis/CLAUDE.md`'s implementation status reflects Phase 2.
- [ ] No API keys or `.env` files committed.
- [ ] All work is committed and pushed to GitHub.

---

# Week 20 Reflection

Write 200–300 words answering:

1. What did you build this week?
2. Why does this project use NetworkX instead of a graph database?
3. What error did you encounter, and how did you fix it?
4. How did you verify the extraction pipeline actually works, beyond trusting the code?
5. What would you improve, or which relation type/query would you add next?

Save as:

```text
week20_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Knowledge graph | A graph where nodes are entities and edges are typed, evidenced relationships |
| Directed graph | A graph where each edge has a direction (source to target) |
| Degree centrality | A ranking of nodes by how many edges connect to them |
| Inline XBRL | Machine-readable financial tag data embedded directly in a filing's HTML |
| Node-link format | A JSON representation of a graph as a list of nodes and a list of edges |
| Injected-callable pattern | Passing a function (e.g. `generate`) as a parameter instead of hardcoding a dependency |

---

# Week Summary

During Week 20, you:

- learned why company relationship data fits a graph model, and why NetworkX (not a graph database server) fits this course's scope;
- turned cached filing HTML into clean prompt text, fixing a real bug where hidden inline-XBRL metadata polluted the extracted text;
- built pydantic schemas that structurally constrain an LLM's output to valid entity and relationship types;
- used the same injected-callable pattern from Week 17 to keep extraction provider-agnostic and testable without an API key;
- built, queried, persisted, and visualized a NetworkX knowledge graph;
- wired two new commands into the `sec_thesis` CLI, building on Week 18's foundation rather than starting over.

---

# Suggested Reading

## Required

- NetworkX documentation, "Tutorial" and "Drawing"
- BeautifulSoup documentation, "Quick Start"

## Recommended

- SEC's inline XBRL viewer documentation (context for §2.1's hidden-metadata fix)
- `src/sec_thesis/CLAUDE.md` — read it again after finishing this week; Phase 2's implementation status now reflects what you built

---

# Where to Go From Here

Phase 2 is deliberately narrow: two entity/relationship types worth of extraction, an in-memory graph, no persistence beyond a single JSON file. The full `sec_thesis` spec (`CLAUDE.md`) still has more to build:

- **`xbrl.py`** — structured extraction of the numeric XBRL facts this week's `display:none` fix deliberately stripped out as noise; a future phase would parse them as data instead of discarding them.
- **`analysis/` and `build-thesis`** — using the knowledge graph as one more input (alongside DCF numbers from Week 17 and raw filing text) to synthesize a full investment thesis.
- **Graduating to a real graph database** — if the entity count grows past what fits comfortably in memory, or multiple processes need to query the graph concurrently, Neo4j (or a similar graph database) becomes the right trade-off instead of NetworkX.
- **`reporting/`** — rendering the graph and its query results into the Markdown/JSON research output Week 17/18 already established a pattern for.

Each is its own small, testable phase — not a single large jump.
