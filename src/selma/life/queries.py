"""SPARQL query builders for selma.life.

Pure functions that interpolate concrete terms (URIs, typed datetime
literals) — the underlying ``MemoryAPI.ask`` does not support variable
bindings for SELECT in the current implementation, so datetimes are
interpolated as ``xsd:dateTime`` typed literals.
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

_VFROM = core.PROPS["validFrom"]
_VTO = core.PROPS["validTo"]
_LABEL = core.PROPS["label"]
_TAG = core.PROPS["tag"]
_PARTOF = core.PROPS["partOf"]

# URI prefixes that distinguish life entities (all are selma:Event instances).
_ACTIVITY_NS = "https://selma.example/ns/life#activity/"


def _term(s: str) -> str:
    """Serialize a subject: a SPARQL variable (``?x``) or a full URI."""
    if s.startswith("?"):
        return s
    return f"<{s}>"


def _fact_value(subj: str, pred_uri: str, var: str, fact_var: str = "f") -> str:
    """Join a subject to its *current* reified fact and project a value.

    ``subj`` is either a full URI string or a SPARQL variable (``?r``).
    ``fact_var`` is the SPARQL variable name used for the reification node
    — each OPTIONAL block MUST use a distinct fact variable, otherwise an
    earlier binding pins the join and later blocks fail to match.

    Only facts whose reification node has no ``selma:validTo`` (i.e. not
    retired by ``forget(soft=True)``) are matched, so stale values from
    superseded/retired facts do not leak into the result. The optional
    block binds ``var`` to the object of the reified triple whose
    predicate is ``pred_uri``; unbound when no such current fact exists.
    """
    return (f"OPTIONAL {{ ?{fact_var} <{_RDF_SUBJECT}> {_term(subj)} ; "
            f"<{_RDF_PREDICATE}> <{pred_uri}> ; "
            f"<{_RDF_OBJECT}> ?{var} . "
            f"FILTER NOT EXISTS {{ ?{fact_var} <{_VTO}> ?{fact_var}vt }} }}")


def reminder_get(uri: str) -> str:
    """SELECT a single reminder's fire time, label, about, firedAt."""
    body = (
        f"GRAPH ?g {{ <{uri}> a <{core.uri('Reminder')}> }} . "
        f"{_fact_value(uri, _VFROM, 'vf', 'fv')} . "
        f"{_fact_value(uri, _LABEL, 'label', 'fl')} . "
        f"{_fact_value(uri, PROPS['remindsAbout'], 'about', 'fa')} . "
        f"{_fact_value(uri, PROPS['firedAt'], 'fired', 'ff')}"
    )
    return (f"{prologue()}\n"
            f"SELECT ?vf ?label ?about ?fired WHERE {{ {body} }} LIMIT 1")


def reminder_list(*, due_before, include_fired) -> str:
    """SELECT all reminders, optionally filtered by due time / fired state."""
    conds = []
    if not include_fired:
        conds.append(f"!BOUND(?fired)")
    if due_before is not None:
        conds.append(f"?vf <= {_dt(due_before)}")
    filt = f"FILTER({' && '.join(conds)})" if conds else ""
    body = (
        f"GRAPH ?g {{ ?r a <{core.uri('Reminder')}> }} . "
        f"{_fact_value('?r', _VFROM, 'vf', 'fv')} . "
        f"{_fact_value('?r', _LABEL, 'label', 'fl')} . "
        f"{_fact_value('?r', PROPS['remindsAbout'], 'about', 'fa')} . "
        f"{_fact_value('?r', PROPS['firedAt'], 'fired', 'ff')}"
    )
    where = f"{{ {body}"
    if filt:
        where += f" {filt}"
    where += " }"
    return (f"{prologue()}\n"
            f"SELECT ?r ?vf ?label ?about ?fired WHERE {where}")


def reminder_check_due(now: str) -> str:
    """SELECT unfired reminders whose validFrom <= now."""
    body = (
        f"GRAPH ?g {{ ?r a <{core.uri('Reminder')}> }} . "
        f"?r <{_VFROM}> ?vf . "
        f"FILTER NOT EXISTS {{ ?r <{PROPS['firedAt']}> ?f }} . "
        f"FILTER(?vf <= {_dt(now)})"
    )
    return (f"{prologue()}\n"
            f"SELECT ?r WHERE {{ {body} }}")


def schedule_get(uri: str) -> str:
    """SELECT a single scheduled event's start, end, label, partOf."""
    body = (
        f"GRAPH ?g {{ <{uri}> a <{core.uri('Event')}> }} . "
        f"{_fact_value(uri, _VFROM, 'start', 'fs')} . "
        f"{_fact_value(uri, _VTO, 'end', 'fe')} . "
        f"{_fact_value(uri, _LABEL, 'label', 'fl')} . "
        f"{_fact_value(uri, _PARTOF, 'part', 'fp')}"
    )
    return (f"{prologue()}\n"
            f"SELECT ?start ?end ?label ?part WHERE {{ {body} }} LIMIT 1")


def schedule_list(*, day, week) -> str:
    """SELECT scheduled events whose start falls in [start, end)."""
    if day is not None:
        lo = f"{day}T00:00:00"
        hi = f"{day}T23:59:59"
    else:
        lo = f"{week}T00:00:00"
        hi = f"{week}T23:59:59"
        # Week = 7 days from the given Monday.
        # We widen the upper bound by adding 6 days; simpler to just filter
        # start < Monday+7. Interpolate a literal far enough ahead.
    body = (
        f"GRAPH ?g {{ ?uri a <{core.uri('Event')}> }} . "
        f"{_fact_value('?uri', _VFROM, 'start', 'fs')} . "
        f"{_fact_value('?uri', _VTO, 'end', 'fe')} . "
        f"{_fact_value('?uri', _LABEL, 'label', 'fl')} . "
        f"{_fact_value('?uri', _PARTOF, 'part', 'fp')}"
    )
    if week is not None:
        # Filter start within the 7-day window starting at the Monday.
        filt = (f"FILTER(BOUND(?start) && ?start >= {_dt(lo)} && "
                f"?start < {_dt(week_plus_days(week, 7))})")
    else:
        filt = (f"FILTER(BOUND(?start) && ?start >= {_dt(lo)} && "
                f"?start <= {_dt(hi)})")
    return (f"{prologue()}\n"
            f"SELECT ?uri ?start ?end ?label ?part WHERE {{ {body} {filt} }}")


def week_plus_days(monday: str, n: int) -> str:
    """Add ``n`` days to a ``YYYY-MM-DD`` date string, return ISO datetime."""
    from datetime import datetime, timedelta
    d = datetime.strptime(monday, "%Y-%m-%d") + timedelta(days=n)
    return d.strftime("%Y-%m-%dT00:00:00")


def schedule_conflicts(start: str, end: str, *, exclude) -> str:
    """SELECT event URIs overlapping [start, end)."""
    conds = [f"?s < {_dt(end)}", f"?t > {_dt(start)}"]
    if exclude is not None:
        conds.append(f"?e != <{exclude}>")
    filt = f"FILTER({' && '.join(conds)})"
    body = (
        f"GRAPH ?g {{ ?e a <{core.uri('Event')}> }} . "
        f"?e <{_VFROM}> ?s . "
        f"?e <{_VTO}> ?t"
    )
    return (f"{prologue()}\n"
            f"SELECT ?e WHERE {{ {body} {filt} }}")


def activity_current() -> str:
    """SELECT the running activity (Event with no validTo)."""
    body = (
        f"GRAPH ?g {{ ?a a <{core.uri('Event')}> }} . "
        f"?a <{_VFROM}> ?start . "
        f"FILTER(STRSTARTS(STR(?a), \"{_ACTIVITY_NS}\")) . "
        f"FILTER NOT EXISTS {{ ?a <{_VTO}> ?vt }}"
    )
    return (f"{prologue()}\n"
            f"SELECT ?a ?start WHERE {{ {body} }} LIMIT 1")


def activity_history(*, since, until, tags) -> str:
    """SELECT activities (Events under the life:activity/ URI prefix).

    Includes both running (unbounded ``validTo``) and completed activities;
    ``current()`` is the dedicated accessor for the running one. Activities
    are distinguished from scheduled events by their ``life:activity/`` URI
    prefix (spec §3: both are ``selma:Event``).
    """
    conds = [f"STRSTARTS(STR(?uri), \"{_ACTIVITY_NS}\")"]
    if since is not None:
        conds.append(f"?start >= {_dt(since)}")
    if until is not None:
        conds.append(f"?start <= {_dt(until)}")
    # Tag filtering: require at least one selma:tag in `tags`.
    tag_clauses = ""
    if tags:
        unions = " UNION ".join(
            f"{{ ?ft <{_RDF_SUBJECT}> ?uri ; "
            f"<{_RDF_PREDICATE}> <{_TAG}> ; "
            f"<{_RDF_OBJECT}> {serialize_term(_str_literal(t))} }}"
            for t in tags)
        tag_clauses = f" . {unions}"
    body = (
        f"GRAPH ?g {{ ?uri a <{core.uri('Event')}> }} . "
        f"{_fact_value('?uri', _VFROM, 'start', 'fs')} . "
        f"{_fact_value('?uri', _VTO, 'end', 'fe')} . "
        f"{_fact_value('?uri', _LABEL, 'label', 'fl')} . "
        f"{_fact_value('?uri', _PARTOF, 'part', 'fp')}"
        f"{tag_clauses}"
    )
    filt = f"FILTER({' && '.join(conds)})"
    return (f"{prologue()}\n"
            f"SELECT ?uri ?start ?end ?label ?part WHERE {{ {body} {filt} }}")


def activity_tags(uri: str) -> str:
    """SELECT all selma:tag values for a given activity URI."""
    body = (
        f"?f <{_RDF_SUBJECT}> <{uri}> ; "
        f"<{_RDF_PREDICATE}> <{_TAG}> ; "
        f"<{_RDF_OBJECT}> ?tag"
    )
    return (f"{prologue()}\n"
            f"SELECT ?tag WHERE {{ {body} }}")


def _str_literal(value: str) -> "Literal":
    from pyoxigraph import Literal
    return Literal(value)


def activity_is_running(uri: str) -> str:
    """ASK whether the given activity has no validTo (still running)."""
    body = (
        f"GRAPH ?g {{ <{uri}> a <{core.uri('Event')}> }} . "
        f"<{uri}> <{_VFROM}> ?start . "
        f"FILTER NOT EXISTS {{ <{uri}> <{_VTO}> ?vt }}"
    )
    return (f"{prologue()}\n"
            f"ASK WHERE {{ {body} }}")