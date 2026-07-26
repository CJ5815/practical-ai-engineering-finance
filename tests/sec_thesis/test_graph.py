from sec_thesis.graph import (
    build_graph,
    competitors_of,
    load_graph,
    most_central_entities,
    save_graph,
    visualize_graph,
)
from sec_thesis.llm.extraction import Entity, ExtractionResult, Relationship

SAMPLE_RESULT = ExtractionResult(
    entities=[
        Entity(name="Apple Inc.", entity_type="company", ticker="AAPL"),
        Entity(name="Samsung Electronics", entity_type="company", ticker=None),
        Entity(name="Qualcomm", entity_type="company", ticker="QCOM"),
        Entity(name="Tim Cook", entity_type="person", ticker=None),
    ],
    relationships=[
        Relationship(
            source="Apple Inc.",
            target="Samsung Electronics",
            relation_type="competitor_of",
            evidence="we compete with Samsung Electronics",
        ),
        Relationship(
            source="Apple Inc.",
            target="Qualcomm",
            relation_type="supplier_of",
            evidence="Qualcomm supplies components",
        ),
        Relationship(
            source="Tim Cook",
            target="Apple Inc.",
            relation_type="executive_of",
            evidence="Tim Cook, Chief Executive Officer",
        ),
    ],
)


def test_build_graph_creates_nodes_and_edges() -> None:
    graph = build_graph([SAMPLE_RESULT])

    assert graph.number_of_nodes() == 4
    assert graph.number_of_edges() == 3
    assert graph.nodes["Apple Inc."]["ticker"] == "AAPL"
    assert graph["Apple Inc."]["Samsung Electronics"]["relation_type"] == "competitor_of"


def test_competitors_of_finds_both_directions() -> None:
    graph = build_graph([SAMPLE_RESULT])

    assert competitors_of(graph, "Apple Inc.") == ["Samsung Electronics"]
    assert competitors_of(graph, "Samsung Electronics") == ["Apple Inc."]


def test_most_central_entities_ranks_apple_highest() -> None:
    graph = build_graph([SAMPLE_RESULT])

    ranked = most_central_entities(graph, top_n=1)

    assert ranked[0][0] == "Apple Inc."


def test_save_and_load_graph_round_trips(tmp_path) -> None:
    graph = build_graph([SAMPLE_RESULT])
    path = tmp_path / "graph.json"

    save_graph(graph, path)
    loaded = load_graph(path)

    assert loaded.number_of_nodes() == graph.number_of_nodes()
    assert loaded.number_of_edges() == graph.number_of_edges()
    assert loaded["Apple Inc."]["Samsung Electronics"]["relation_type"] == "competitor_of"
    assert competitors_of(loaded, "Apple Inc.") == ["Samsung Electronics"]


def test_visualize_graph_writes_a_file(tmp_path) -> None:
    graph = build_graph([SAMPLE_RESULT])
    path = tmp_path / "graph.png"

    visualize_graph(graph, path)

    assert path.exists()
    assert path.stat().st_size > 0
