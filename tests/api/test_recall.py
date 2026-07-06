from pyoxigraph import Literal, NamedNode

from selma.memory import terms


def test_recall_filters_by_subject(fresh_api):
    sa = NamedNode("http://ex/a")
    sb = NamedNode("http://ex/b")
    p = NamedNode("http://ex/p")
    fresh_api.remember(sa, p, Literal("1"), stated_by=NamedNode("selma:self"))
    fresh_api.remember(sb, p, Literal("2"), stated_by=NamedNode("selma:self"))
    rows = fresh_api.recall(sa)
    assert len(rows) == 1
    assert rows[0]["o"].value == "1"


def test_recall_history_includes_superseded(fresh_api):
    s = NamedNode("http://ex/a")
    p = NamedNode("http://ex/p")
    fresh_api.remember(s, p, Literal("old"), stated_by=NamedNode("selma:self"),
                      valid_to="2020-01-01T00:00:00")
    fresh_api.remember(s, p, Literal("new"), stated_by=NamedNode("selma:self"),
                      valid_from="2020-01-02T00:00:00")
    current = fresh_api.recall(s, p)
    assert len(current) == 1
    assert current[0]["o"].value == "new"
    history = fresh_api.recall(s, p, include_history=True)
    assert len(history) == 2