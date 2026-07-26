"""Build, query, persist, and visualize the entity-relationship knowledge graph.

Deterministic (CLAUDE.md rule 6) — nothing here calls an LLM. It only
assembles what llm.extraction already extracted into a queryable graph.
"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
from matplotlib import pyplot as plt

from sec_thesis.llm.extraction import ExtractionResult

_RELATION_COLORS = {
    "competitor_of": "#d9534f",
    "subsidiary_of": "#5a7bb0",
    "executive_of": "#2a9d3f",
    "supplier_of": "#f0a35a",
}


def build_graph(results: list[ExtractionResult]) -> nx.DiGraph:
    """Assemble one or more extraction results into a single knowledge graph.

    Args:
        results: Extraction results, e.g. one per filing.

    Returns:
        A directed graph. Nodes are entity names; edges carry
        relation_type and evidence. Building the graph from multiple
        filings that mention the same entity or relationship merges them
        onto the same node/edge rather than duplicating.
    """
    graph = nx.DiGraph()
    for result in results:
        for entity in result.entities:
            graph.add_node(entity.name, entity_type=entity.entity_type, ticker=entity.ticker)
        for rel in result.relationships:
            graph.add_edge(
                rel.source,
                rel.target,
                relation_type=rel.relation_type,
                evidence=rel.evidence,
            )
    return graph


def save_graph(graph: nx.DiGraph, path: str | Path) -> None:
    """Save a graph as JSON (node-link format)."""
    data = nx.node_link_data(graph, edges="edges")
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_graph(path: str | Path) -> nx.DiGraph:
    """Load a graph previously saved with save_graph."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return nx.node_link_graph(data, edges="edges")


def competitors_of(graph: nx.DiGraph, name: str) -> list[str]:
    """Find every entity connected to `name` by a competitor_of edge, in either direction."""
    found = []
    for _, target, data in graph.out_edges(name, data=True):
        if data.get("relation_type") == "competitor_of":
            found.append(target)
    for source, _, data in graph.in_edges(name, data=True):
        if data.get("relation_type") == "competitor_of":
            found.append(source)
    return found


def most_central_entities(graph: nx.DiGraph, top_n: int = 5) -> list[tuple[str, float]]:
    """Rank entities by degree centrality — how many relationships mention them.

    Returns:
        Up to `top_n` (name, centrality) pairs, highest centrality first.
    """
    centrality = nx.degree_centrality(graph)
    return sorted(centrality.items(), key=lambda item: item[1], reverse=True)[:top_n]


def visualize_graph(graph: nx.DiGraph, path: str | Path) -> None:
    """Draw the graph and save it as a PNG, colored by relation_type."""
    fig, ax = plt.subplots(figsize=(10, 8))
    pos = nx.spring_layout(graph, seed=42)

    edge_colors = [
        _RELATION_COLORS.get(data.get("relation_type"), "#999999")
        for _, _, data in graph.edges(data=True)
    ]
    nx.draw(
        graph,
        pos,
        ax=ax,
        with_labels=True,
        node_color="#ddeaff",
        edge_color=edge_colors,
        node_size=2000,
        font_size=8,
        arrows=True,
    )
    ax.set_title("Company Relationship Knowledge Graph")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
