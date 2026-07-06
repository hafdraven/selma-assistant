import pytest
from pyoxigraph import Literal, NamedNode

from selma.memory import terms
from selma.memory.exceptions import ProvenanceError


def test_remember_stores_fact(fresh_api):
    s = NamedNode("http://ex/alice")
    p = NamedNode("http://ex/knows")
    o = NamedNode("http://ex/bob")
    self_agent = NamedNode(terms.uri("Agent"))  # not really, but a stand-in URI
    stated_by = NamedNode("selma:agent:self")
    fresh_api.remember(s, p, o, stated_by=stated_by, source=NamedNode("voice:alexa"))
    rows = fresh_api.recall(s, p, o)
    assert len(rows) == 1
    assert rows[0]["o"].value == "http://ex/bob"


def test_remember_requires_stated_by(fresh_api):
    with pytest.raises(ProvenanceError):
        fresh_api.remember(NamedNode("http://ex/a"), NamedNode("http://ex/p"),
                           Literal("x"), stated_by=None)


def test_remember_records_provenance(fresh_api):
    s = NamedNode("http://ex/a")
    p = NamedNode("http://ex/p")
    o = Literal("v")
    fresh_api.remember(s, p, o, stated_by=NamedNode("selma:agent:self"),
                      confidence=0.8, source=NamedNode("voice:alexa"))
    # Confidence is queryable via ask.
    rows = list(fresh_api.ask(
        "SELECT ?c WHERE { ?s selma:confidence ?c }"))
    assert float(rows[0]["c"].value) == 0.8