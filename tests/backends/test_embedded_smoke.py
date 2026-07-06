from pyoxigraph import DefaultGraph, Literal, NamedNode

from selma.memory.backends.embedded import EmbeddedOxigraph


def test_add_and_query(tmp_path):
    store = EmbeddedOxigraph(path=tmp_path / "s")
    ex = NamedNode("http://example/")
    store.add(None, ex, NamedNode("http://example/p"), Literal("hi"),
              ctx=NamedNode("http://example/g"))
    rows = list(store.query("SELECT ?o WHERE { GRAPH ?g { ?s ?p ?o } }"))
    assert rows[0]["o"].value == "hi"
    store.close()


def test_count(tmp_path):
    store = EmbeddedOxigraph(path=tmp_path / "s")
    g = NamedNode("http://example/g")
    store.add(None, NamedNode("http://example/s"), NamedNode("http://example/p"),
              Literal("x"), ctx=g)
    store.add(None, NamedNode("http://example/s"), NamedNode("http://example/p"),
              Literal("y"), ctx=g)
    assert store.count(None, None, None, ctx=g) == 2
    store.close()


def test_update_deletes(tmp_path):
    store = EmbeddedOxigraph(path=tmp_path / "s")
    g = NamedNode("http://example/g")
    store.add(None, NamedNode("http://example/s"), NamedNode("http://example/p"),
              Literal("x"), ctx=g)
    store.update("DELETE WHERE { GRAPH <http://example/g> { ?s ?p ?o } }")
    assert store.count(None, None, None, ctx=g) == 0
    store.close()