import pytest
from pyoxigraph import Literal, NamedNode

from selma.memory import terms
from selma.memory.exceptions import ProvenanceError, QueryError


def test_forget_soft_sets_validto(fresh_api):
    s = NamedNode("http://ex/a")
    p = NamedNode("http://ex/p")
    fresh_api.remember(s, p, Literal("v"), stated_by=NamedNode("selma:self"),
                      valid_from="2030-01-01T00:00:00")
    n = fresh_api.forget(s, p, soft=True)
    assert n >= 1
    # A recall in the present (as_of default) no longer sees it.
    rows = fresh_api.recall(s, p)
    assert len(rows) == 0


def test_forget_hard_requires_reason(fresh_api):
    s = NamedNode("http://ex/a")
    p = NamedNode("http://ex/p")
    fresh_api.remember(s, p, Literal("v"), stated_by=NamedNode("selma:self"))
    with pytest.raises(ProvenanceError):
        fresh_api.forget(s, p, soft=False, reason=None)


def test_forget_all_none_rejected(fresh_api):
    with pytest.raises(QueryError):
        fresh_api.forget(soft=True)


def test_forget_hard_removes_and_audits(fresh_api):
    s = NamedNode("http://ex/a")
    p = NamedNode("http://ex/p")
    fresh_api.remember(s, p, Literal("v"), stated_by=NamedNode("selma:self"))
    fresh_api.forget(s, p, soft=False, reason="test-cleanup")
    assert fresh_api.recall(s, p) == []
    # Audit graph still has an entry.
    audit_rows = list(fresh_api.ask(
        "SELECT ?s WHERE { GRAPH <https://selma.example/ns/core#audit> { ?s ?p ?o } }"))
    assert len(audit_rows) >= 1