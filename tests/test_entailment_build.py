from pyoxigraph import Literal, NamedNode

from selma.memory import terms
from selma.memory.entailment import (inverse_of, is_transitive, subclass_expand)
from selma.memory.sparql import serialize_term


def test_serialize_namednode():
    assert serialize_term(NamedNode("http://ex/s")) == "<http://ex/s>"


def test_serialize_plain_literal():
    assert serialize_term(Literal("hi")) == '"hi"'


def test_serialize_datetime_literal():
    assert serialize_term(Literal("2024-01-01T00:00:00",
                      datatype=NamedNode(terms.XSD["dateTime"]))).startswith(
        '"2024-01-01T00:00:00"^^<http://www.w3.org/2001/XMLSchema#dateTime>')


def test_serialize_escapes_quotes():
    assert serialize_term(Literal('a"b')) == r'"a\"b"'


def test_subclass_expand_entity_returns_all():
    subs = set(subclass_expand(terms.uri("Entity")))
    # Entity itself plus every subclass (transitive closure)
    assert terms.uri("Agent") in subs
    assert terms.uri("Reminder") in subs  # Reminder -> Event -> Entity
    assert terms.uri("Entity") in subs


def test_subclass_expand_task_returns_just_task():
    assert subclass_expand(terms.uri("Task")) == [terms.uri("Task")]


def test_inverse_of_relates():
    assert inverse_of(terms.uri("relates")) == terms.uri("relatedBy")
    assert inverse_of(terms.uri("relatedBy")) == terms.uri("relates")


def test_is_transitive_partof():
    assert is_transitive(terms.uri("partOf")) is True
    assert is_transitive(terms.uri("label")) is False