import pytest
from pyoxigraph import NamedNode

from selma.memory import terms
from selma.memory.exceptions import ProvenanceError


def test_relate_stores_relationship(fresh_api):
    # Open-ended relationship (no valid_to): still current, so recall sees it.
    fresh_api.relate(NamedNode("http://ex/alice"),
                     NamedNode("http://ex/workedFor"),
                     NamedNode("http://ex/bob"),
                     stated_by=NamedNode("selma:self"),
                     valid_from="2020-01-01T00:00:00")
    rows = fresh_api.recall(NamedNode("http://ex/alice"),
                            NamedNode("http://ex/workedFor"))
    assert len(rows) == 1


def test_relate_requires_provenance(fresh_api):
    with pytest.raises(ProvenanceError):
        fresh_api.relate(NamedNode("http://ex/a"), NamedNode("http://ex/p"),
                         NamedNode("http://ex/b"), stated_by=None)