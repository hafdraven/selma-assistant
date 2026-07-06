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