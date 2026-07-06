"""Embedded-only: data persists across close/reopen (spec §3 durability)."""
from pyoxigraph import Literal, NamedNode

from selma.memory.backends.embedded import EmbeddedOxigraph


def test_persistence_across_reopen(tmp_path):
    p = tmp_path / "store"
    s = EmbeddedOxigraph(path=p)
    g = NamedNode("http://ex/g")
    s.add(None, NamedNode("http://ex/s"), NamedNode("http://ex/p"),
          Literal("durable"), ctx=g)
    s.close()

    s2 = EmbeddedOxigraph(path=p)
    assert s2.count(None, None, None, ctx=g) == 1
    rows = list(s2.query("SELECT ?o WHERE { GRAPH <http://ex/g> { ?s ?p ?o } }"))
    assert rows[0]["o"].value == "durable"
    s2.close()