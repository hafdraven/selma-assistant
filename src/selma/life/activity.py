"""ActivityService — capture what the user is doing (spec §3, §4).

Activities are ``selma:Event`` instances with a start (``validFrom``),
optional end (``validTo`` — set on stop), ``label``, ``tag`` values, and
optional ``partOf``. Unbounded ``validTo`` = running; bounded = completed.
v1 enforces a single running activity.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pyoxigraph import Literal, NamedNode

from selma.memory import terms as core

from . import queries
from .exceptions import (ActivityAlreadyRunningError, ActivityNotRunningError)
from .models import Activity
from .terms import default_stated_by, instance


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _dt_literal(value: str) -> Literal:
    return Literal(value, datatype=NamedNode(core.XSD["dateTime"]))


class ActivityService:
    def __init__(self, memory, *, stated_by) -> None:
        if stated_by is None:
            stated_by = default_stated_by()
        self._mem = memory
        self._stated_by = stated_by

    # -- writes --
    def start(self, label: str, *, tags=(), part_of=None, at=None) -> str:
        if self.current() is not None:
            raise ActivityAlreadyRunningError(
                "an activity is already running; stop it first")
        at = at or _now_iso()
        u = instance("activity")
        node = NamedNode(u)
        self._mem.ask(
            f"INSERT DATA {{ GRAPH <{core.uri('default')}> "
            f"{{ <{u}> a <{core.uri('Event')}> }} }}")
        self._mem.remember(node, NamedNode(core.PROPS["validFrom"]),
                           _dt_literal(at), stated_by=self._stated_by)
        self._mem.remember(node, NamedNode(core.PROPS["label"]),
                           Literal(label), stated_by=self._stated_by)
        for t in tags:
            self._mem.remember(node, NamedNode(core.PROPS["tag"]),
                               Literal(t), stated_by=self._stated_by)
        if part_of is not None:
            if isinstance(part_of, str):
                part_of = NamedNode(part_of)
            self._mem.remember(node, NamedNode(core.PROPS["partOf"]),
                               part_of, stated_by=self._stated_by)
        return u

    def stop(self, uri: str, *, at=None) -> None:
        at = at or _now_iso()
        # Verify it is running (no validTo) before stopping. ASK returns a
        # QueryBoolean; bool() on it yields True if the pattern matches.
        running = bool(self._mem.ask(queries.activity_is_running(uri)))
        if not running:
            raise ActivityNotRunningError(f"{uri} is not running")
        self._mem.remember(NamedNode(uri), NamedNode(core.PROPS["validTo"]),
                           _dt_literal(at), stated_by=self._stated_by)

    # -- reads --
    def current(self) -> Activity | None:
        rows = list(self._mem.ask(queries.activity_current()))
        if not rows:
            return None
        u = rows[0]["a"].value
        # Fetch full detail (label, tags, part_of).
        return self._load_activity(u, rows[0]["start"].value)

    def history(self, *, since=None, until=None, tags=()) -> list[Activity]:
        q = queries.activity_history(since=since, until=until, tags=tags)
        rows = list(self._mem.ask(q))
        out = []
        for r in rows:
            u = r["uri"].value
            a = Activity.from_row(r)
            a.tags = self._load_tags(u)
            out.append(a)
        out.sort(key=lambda a: a.start or "")
        return out

    # -- helpers --
    def _load_activity(self, u: str, start: str) -> Activity:
        # Reuse the schedule_get query shape for label/part_of, plus tags.
        a = Activity(uri=u, start=start)
        # Read label and part_of via recall.
        for row in self._mem.recall(NamedNode(u), NamedNode(core.PROPS["label"])):
            a.label = row["o"].value
            break
        for row in self._mem.recall(NamedNode(u), NamedNode(core.PROPS["partOf"])):
            a.part_of = row["o"].value
            break
        a.tags = self._load_tags(u)
        return a

    def _load_tags(self, u: str) -> list[str]:
        tags = [row["tag"].value for row in self._mem.ask(queries.activity_tags(u))]
        return sorted(set(tags))