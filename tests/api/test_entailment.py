from pyoxigraph import Literal, NamedNode

from selma.memory import terms


def _seed(api):
    api.ask("INSERT DATA { GRAPH <selma:g> { "
            "<http://ex/alice> a selma:Agent ; selma:label 'Alice' . "
            "<http://ex/proj> a selma:Project ; selma:label 'Proj' . "
            "<http://ex/rem> a selma:Reminder ; selma:label 'Rem' . "
            "} }")


def test_subclass_entailment_find_entity(fresh_api):
    _seed(fresh_api)
    found = {f.value for f in fresh_api.find(terms.uri("Entity"))}
    assert "http://ex/alice" in found
    assert "http://ex/proj" in found
    assert "http://ex/rem" in found


def test_subclass_entailment_find_event_excludes_project(fresh_api):
    _seed(fresh_api)
    found = {f.value for f in fresh_api.find(terms.uri("Event"))}
    assert "http://ex/rem" in found   # Reminder is subclass of Event
    assert "http://ex/proj" not in found


def test_transitive_partof(fresh_api):
    fresh_api.ask("INSERT DATA { GRAPH <selma:g> { "
                  "<http://ex/a> selma:partOf <http://ex/b> . "
                  "<http://ex/b> selma:partOf <http://ex/c> . } }")
    rows = list(fresh_api.ask(
        "SELECT ?x WHERE { GRAPH ?g { <http://ex/a> selma:partOf+ ?x } }"))
    vals = {r["x"].value for r in rows}
    assert vals == {"http://ex/b", "http://ex/c"}