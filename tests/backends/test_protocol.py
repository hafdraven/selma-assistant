"""Conformance suite — every Backend implementation must pass these."""
from __future__ import annotations

import pytest
from pyoxigraph import DefaultGraph, Literal, NamedNode

S = NamedNode("http://ex/s")
P = NamedNode("http://ex/p")
O = Literal("o")
G1 = NamedNode("http://ex/g1")
G2 = NamedNode("http://ex/g2")


def test_add_and_select(backend):
    backend.add(None, S, P, O, ctx=G1)
    rows = list(backend.query("SELECT ?o WHERE { GRAPH ?g { ?s ?p ?o } }"))
    assert rows[0]["o"].value == "o"


def test_named_graph_isolation(backend):
    backend.add(None, S, P, Literal("in-g1"), ctx=G1)
    backend.add(None, S, P, Literal("in-g2"), ctx=G2)
    only_g1 = list(backend.query(
        "SELECT ?o WHERE { GRAPH <http://ex/g1> { ?s ?p ?o } }"))
    assert [r["o"].value for r in only_g1] == ["in-g1"]


def test_pattern_remove(backend):
    backend.add(None, S, P, O, ctx=G1)
    backend.remove(None, None, None, None, ctx=G1)
    assert backend.count(None, None, None, ctx=G1) == 0


def test_ask_query(backend):
    backend.add(None, S, P, O, ctx=G1)
    result = backend.query("ASK WHERE { GRAPH ?g { ?s ?p ?o } }")
    assert bool(result) is True


def test_construct_query(backend):
    backend.add(None, S, P, O, ctx=G1)
    triples = list(backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"))
    assert len(list(triples)) == 1


def test_update_inserts_and_deletes(backend):
    backend.update(
        "INSERT DATA { GRAPH <http://ex/g1> { "
        "<http://ex/a> <http://ex/p> 'x' } }")
    assert backend.count(None, None, None, ctx=G1) == 1
    backend.update("DELETE WHERE { GRAPH <http://ex/g1> { ?s ?p ?o } }")
    assert backend.count(None, None, None, ctx=G1) == 0


def test_query_error_on_bad_sparql(backend):
    from selma.memory.exceptions import QueryError
    with pytest.raises(QueryError):
        backend.query("SELECT ?s WHERE { ??? }")


def test_count_default_graph(backend):
    backend.add(None, S, P, O, ctx=DefaultGraph())
    assert backend.count(None, None, None, ctx=DefaultGraph()) == 1