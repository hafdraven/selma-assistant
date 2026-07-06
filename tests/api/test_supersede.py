import pytest
from pyoxigraph import Literal, NamedNode

from selma.memory import terms
from selma.memory.exceptions import SupersedeError


def test_supersede_marks_old_and_inserts_new(fresh_api):
    s = NamedNode("http://ex/a")
    p = NamedNode("http://ex/p")
    old = fresh_api.remember(s, p, Literal("old"), stated_by=NamedNode("selma:self"))
    new = fresh_api.supersede(s, Literal("new"), stated_by=NamedNode("selma:self"),
                             reason="corrected")
    # Current recall sees only the new value.
    rows = fresh_api.recall(s, p)
    assert any(r["o"].value == "new" for r in rows)
    # History sees both.
    hist = fresh_api.recall(s, p, include_history=True)
    assert len(hist) >= 2


def test_supersede_refuses_already_superseded(fresh_api):
    s = NamedNode("http://ex/a")
    p = NamedNode("http://ex/p")
    fresh_api.remember(s, p, Literal("v1"), stated_by=NamedNode("selma:self"),
                      valid_to="2020-01-01T00:00:00")
    with pytest.raises(SupersedeError):
        fresh_api.supersede(s, Literal("v2"), stated_by=NamedNode("selma:self"))