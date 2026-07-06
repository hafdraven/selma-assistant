"""SPARQL query builders for selma.agents.

Pure functions that interpolate concrete terms (URIs, typed datetime literals,
string literals). Reuses the reified-fact join pattern from selma.life.queries
to read current property values while ignoring superseded/retired facts.
"""
from __future__ import annotations

from selma.memory import terms as core
from selma.memory.sparql import _dt, serialize_term

from .terms import PROPS, prologue

# Reified-fact predicate IRIs (stored on the blank-node fact, joined via
# rdf:subject). Used to read property values that remember() wrote.
_RDF_SUBJECT = "http://www.w3.org/1999/02/22-rdf-syntax-ns#subject"
_RDF_PREDICATE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#predicate"
_RDF_OBJECT = "http://www.w3.org/1999/02/22-rdf-syntax-ns#object"

_VTO = core.PROPS["validTo"]
_LABEL = core.PROPS["label"]
_DESCRIPTION = core.PROPS["description"]
_HAS_STATUS = core.PROPS["hasStatus"]
_OWNED_BY = core.PROPS["ownedBy"]
_DUE_BY = core.PROPS["dueBy"]
_COMPLETED_AT = core.PROPS["completedAt"]
_PART_OF = core.PROPS["partOf"]
_DEPENDS_ON = core.PROPS["dependsOn"]

_BLOCK_REASON = PROPS["blockReason"]
_EXEC_RESULT = PROPS["executionResult"]


def _term(s: str) -> str:
    """Serialize a subject: a SPARQL variable (``?x``) or a full URI."""
    if s.startswith("?"):
        return s
    return f"<{s}>"


def _fact_value(subj: str, pred_uri: str, var: str, fact_var: str = "f") -> str:
    """Join a subject to its *current* reified fact and project a value.

    Only facts whose reification node has no ``selma:validTo`` (i.e. not
    retired by ``supersede``) are matched, so stale values from superseded
    facts do not leak into the result.
    """
    return (f"OPTIONAL {{ ?{fact_var} <{_RDF_SUBJECT}> {_term(subj)} ; "
            f"<{_RDF_PREDICATE}> <{pred_uri}> ; "
            f"<{_RDF_OBJECT}> ?{var} . "
            f"FILTER NOT EXISTS {{ ?{fact_var} <{_VTO}> ?{fact_var}vt }} }}")


def project_get(uri: str) -> str:
    """SELECT a single project's label, description, partOf."""
    body = (
        f"GRAPH ?g {{ <{uri}> a <{core.uri('Project')}> }} . "
        f"{_fact_value(uri, _LABEL, 'label', 'fl')} . "
        f"{_fact_value(uri, _DESCRIPTION, 'desc', 'fd')} . "
        f"{_fact_value(uri, _PART_OF, 'part', 'fp')}"
    )
    return (f"{prologue()}\n"
            f"SELECT ?label ?desc ?part WHERE {{ {body} }} LIMIT 1")


def project_list() -> str:
    """SELECT all projects with their label, description, partOf."""
    body = (
        f"GRAPH ?g {{ ?uri a <{core.uri('Project')}> }} . "
        f"{_fact_value('?uri', _LABEL, 'label', 'fl')} . "
        f"{_fact_value('?uri', _DESCRIPTION, 'desc', 'fd')} . "
        f"{_fact_value('?uri', _PART_OF, 'part', 'fp')}"
    )
    return (f"{prologue()}\n"
            f"SELECT ?uri ?label ?desc ?part WHERE {{ {body} }}")


def task_get(uri: str) -> str:
    """SELECT a single task's full lifecycle and coordination fields."""
    body = (
        f"GRAPH ?g {{ <{uri}> a <{core.uri('Task')}> }} . "
        f"{_fact_value(uri, _LABEL, 'label', 'fl')} . "
        f"{_fact_value(uri, _DESCRIPTION, 'desc', 'fd')} . "
        f"{_fact_value(uri, _HAS_STATUS, 'status', 'fs')} . "
        f"{_fact_value(uri, _OWNED_BY, 'owner', 'fo')} . "
        f"{_fact_value(uri, _DUE_BY, 'due', 'fdue')} . "
        f"{_fact_value(uri, _COMPLETED_AT, 'completed', 'fc')} . "
        f"{_fact_value(uri, _PART_OF, 'part', 'fp')} . "
        f"{_fact_value(uri, _BLOCK_REASON, 'blockreason', 'fbr')} . "
        f"{_fact_value(uri, _EXEC_RESULT, 'execresult', 'fer')}"
    )
    return (f"{prologue()}\n"
            f"SELECT ?label ?desc ?status ?owner ?due ?completed ?part "
            f"?blockreason ?execresult WHERE {{ {body} }} LIMIT 1")


def task_list(*, project) -> str:
    """SELECT all tasks, optionally filtered to those partOf `project`.

    A task with no partOf (project=None at creation) is included when no
    project filter is given.
    """
    body = (
        f"GRAPH ?g {{ ?uri a <{core.uri('Task')}> }} . "
        f"{_fact_value('?uri', _LABEL, 'label', 'fl')} . "
        f"{_fact_value('?uri', _DESCRIPTION, 'desc', 'fd')} . "
        f"{_fact_value('?uri', _HAS_STATUS, 'status', 'fs')} . "
        f"{_fact_value('?uri', _OWNED_BY, 'owner', 'fo')} . "
        f"{_fact_value('?uri', _DUE_BY, 'due', 'fdue')} . "
        f"{_fact_value('?uri', _COMPLETED_AT, 'completed', 'fc')} . "
        f"{_fact_value('?uri', _PART_OF, 'part', 'fp')} . "
        f"{_fact_value('?uri', _BLOCK_REASON, 'blockreason', 'fbr')} . "
        f"{_fact_value('?uri', _EXEC_RESULT, 'execresult', 'fer')}"
    )
    if project is not None:
        body += f" . FILTER(?part = <{project}>)"
    return (f"{prologue()}\n"
            f"SELECT ?uri ?label ?desc ?status ?owner ?due ?completed ?part "
            f"?blockreason ?execresult WHERE {{ {body} }}")


def task_dependencies(uri: str) -> str:
    """SELECT all current dependsOn targets for a task."""
    body = (
        f"?f <{_RDF_SUBJECT}> <{uri}> ; "
        f"<{_RDF_PREDICATE}> <{_DEPENDS_ON}> ; "
        f"<{_RDF_OBJECT}> ?dep . "
        f"FILTER NOT EXISTS {{ ?f <{_VTO}> ?fvt }}"
    )
    return (f"{prologue()}\nSELECT ?dep WHERE {{ {body} }}")


def task_blockers(uri: str) -> str:
    """SELECT dependsOn targets of `uri` whose hasStatus is not done.

    A dependency blocks if it has no done status (open, in_progress, blocked,
    or no status at all). We match current hasStatus facts and exclude 'done'.
    """
    body = (
        f"?df <{_RDF_SUBJECT}> <{uri}> ; "
        f"<{_RDF_PREDICATE}> <{_DEPENDS_ON}> ; "
        f"<{_RDF_OBJECT}> ?dep . "
        f"FILTER NOT EXISTS {{ ?df <{_VTO}> ?dfvt }} . "
        f"OPTIONAL {{ ?sf <{_RDF_SUBJECT}> ?dep ; "
        f"<{_RDF_PREDICATE}> <{_HAS_STATUS}> ; "
        f"<{_RDF_OBJECT}> ?s . "
        f"FILTER NOT EXISTS {{ ?sf <{_VTO}> ?sfvt }} }} . "
        f"FILTER(!BOUND(?s) || ?s != \"done\")"
    )
    return (f"{prologue()}\nSELECT ?dep WHERE {{ {body} }}")


def blocked_tasks(*, project) -> str:
    """SELECT tasks whose current hasStatus is 'blocked', optionally in project."""
    body = (
        f"GRAPH ?g {{ ?uri a <{core.uri('Task')}> }} . "
        f"?sf <{_RDF_SUBJECT}> ?uri ; "
        f"<{_RDF_PREDICATE}> <{_HAS_STATUS}> ; "
        f"<{_RDF_OBJECT}> \"blocked\" . "
        f"FILTER NOT EXISTS {{ ?sf <{_VTO}> ?sfvt }} . "
        f"{_fact_value('?uri', _LABEL, 'label', 'fl')} . "
        f"{_fact_value('?uri', _PART_OF, 'part', 'fp')} . "
        f"{_fact_value('?uri', _BLOCK_REASON, 'blockreason', 'fbr')} . "
        f"{_fact_value('?uri', _OWNED_BY, 'owner', 'fo')}"
    )
    if project is not None:
        body += f" . FILTER(?part = <{project}>)"
    return (f"{prologue()}\n"
            f"SELECT ?uri ?label ?part ?blockreason ?owner WHERE {{ {body} }}")