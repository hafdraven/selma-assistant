"""ScheduleService — time blocks on a timeline (spec §3, §4).

Scheduled events are ``selma:Event`` instances with ``validFrom`` (start),
``validTo`` (end), optional ``label`` and ``partOf``. Move/cancel use
``forget(soft=True)`` + a fresh ``remember`` (not ``supersede``, which is
ambiguous for multi-fact subjects).
"""
from __future__ import annotations

from datetime import datetime, timezone

from pyoxigraph import Literal, NamedNode

from selma.memory import terms as core

from . import queries
from .exceptions import LifeError, ScheduleConflictError
from .models import ScheduleEvent
from .terms import default_stated_by, instance


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _dt_literal(value: str) -> Literal:
    return Literal(value, datatype=NamedNode(core.XSD["dateTime"]))


class ScheduleService:
    def __init__(self, memory, *, stated_by) -> None:
        if stated_by is None:
            stated_by = default_stated_by()
        self._mem = memory
        self._stated_by = stated_by

    # -- writes --
    def create(self, start: str, end: str, *, label=None, part_of=None) -> str:
        if self.conflicts(start, end):
            raise ScheduleConflictError(
                f"event {start}..{end} overlaps an existing event")
        u = instance("event")
        node = NamedNode(u)
        self._mem.ask(
            f"INSERT DATA {{ GRAPH <{core.uri('default')}> "
            f"{{ <{u}> a <{core.uri('Event')}> }} }}")
        self._mem.remember(node, NamedNode(core.PROPS["validFrom"]),
                           _dt_literal(start), stated_by=self._stated_by)
        self._mem.remember(node, NamedNode(core.PROPS["validTo"]),
                           _dt_literal(end), stated_by=self._stated_by)
        if label is not None:
            self._mem.remember(node, NamedNode(core.PROPS["label"]),
                               Literal(label), stated_by=self._stated_by)
        if part_of is not None:
            if isinstance(part_of, str):
                part_of = NamedNode(part_of)
            self._mem.remember(node, NamedNode(core.PROPS["partOf"]),
                               part_of, stated_by=self._stated_by)
        return u

    def move(self, uri: str, new_start: str, *, new_end=None) -> None:
        ev = self.get(uri)
        new_end = new_end or _shift_end(ev.start, ev.end, new_start)
        if self.conflicts(new_start, new_end, exclude=uri):
            raise ScheduleConflictError(
                f"move to {new_start}..{new_end} overlaps an existing event")
        node = NamedNode(uri)
        # Retire the old start/end facts (soft) then assert fresh ones.
        self._mem.forget(subject=node, predicate=NamedNode(core.PROPS["validFrom"]),
                         soft=True)
        self._mem.forget(subject=node, predicate=NamedNode(core.PROPS["validTo"]),
                         soft=True)
        self._mem.remember(node, NamedNode(core.PROPS["validFrom"]),
                           _dt_literal(new_start), stated_by=self._stated_by)
        self._mem.remember(node, NamedNode(core.PROPS["validTo"]),
                           _dt_literal(new_end), stated_by=self._stated_by)

    def cancel(self, uri: str) -> None:
        node = NamedNode(uri)
        # Retire all current facts about this event.
        self._mem.forget(subject=node, soft=True)
        # Also drop the type assertion from the named graph.
        self._mem.ask(
            f"DELETE WHERE {{ GRAPH <{core.uri('default')}> "
            f"{{ <{uri}> a <{core.uri('Event')}> }} }}")

    # -- reads --
    def get(self, uri: str) -> ScheduleEvent:
        rows = list(self._mem.ask(queries.schedule_get(uri)))
        if not rows:
            raise LifeError(f"event {uri} not found")
        return ScheduleEvent.from_row(rows[0])

    def list(self, *, day=None, week=None) -> list[ScheduleEvent]:
        if day is None and week is None:
            raise ValueError("list requires day= or week=")
        q = queries.schedule_list(day=day, week=week)
        rows = list(self._mem.ask(q))
        out = [ScheduleEvent.from_row(r) for r in rows]
        out.sort(key=lambda e: e.start or "")
        return out

    def conflicts(self, start: str, end: str, *, exclude=None) -> list[str]:
        q = queries.schedule_conflicts(start, end, exclude=exclude)
        return [row["e"].value for row in self._mem.ask(q)]


def _shift_end(old_start: str, old_end: str | None, new_start: str) -> str:
    """Compute the new end preserving the event duration."""
    if old_end is None:
        return new_start
    fmt = "%Y-%m-%dT%H:%M:%S"
    os = datetime.strptime(old_start, fmt)
    oe = datetime.strptime(old_end, fmt)
    ns = datetime.strptime(new_start, fmt)
    dur = oe - os
    return (ns + dur).strftime(fmt)