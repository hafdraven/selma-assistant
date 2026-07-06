from pyoxigraph import Literal, NamedNode

from selma.memory import terms


def test_find_returns_subclass_instances(fresh_api):
    # Insert an Agent (subclass of Entity).
    fresh_api.remember(NamedNode("http://ex/alice"),
                       NamedNode(terms.PROPS["label"]),
                       Literal("Alice"),
                       stated_by=NamedNode("selma:self"))
    fresh_api.ask(
        "INSERT DATA { GRAPH <selma:default> { <http://ex/alice> a selma:Agent } }")
    # find(Entity) should include Agent instances via subclass entailment.
    found = fresh_api.find(terms.uri("Entity"))
    uris = [f.value if hasattr(f, "value") else str(f) for f in found]
    assert "http://ex/alice" in uris


def test_find_with_as_of(fresh_api):
    # An Agent whose sole fact is valid 2020..2023.
    alice = NamedNode("http://ex/alice")
    fresh_api.remember(alice,
                       NamedNode(terms.PROPS["label"]),
                       Literal("Alice"),
                       stated_by=NamedNode("selma:self"),
                       valid_from="2020-01-01T00:00:00",
                       valid_to="2023-01-01T00:00:00")
    fresh_api.ask(
        "INSERT DATA { GRAPH <selma:default> { <http://ex/alice> a selma:Agent } }")
    uris = lambda rows: [f.value if hasattr(f, "value") else str(f)
                        for f in rows]
    # Inside the validity window: found.
    assert "http://ex/alice" in uris(
        fresh_api.find(terms.uri("Entity"), as_of="2022-01-01T00:00:00"))
    # After the validity window: not found.
    assert "http://ex/alice" not in uris(
        fresh_api.find(terms.uri("Entity"), as_of="2024-01-01T00:00:00"))