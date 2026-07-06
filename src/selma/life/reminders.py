"""ReminderService — create, list, fire, and poll reminders (spec §3, §6).

Reminders are ``selma:Reminder`` instances stored via two memory calls:
a type assertion in the ``selma:default`` named graph (so ``find`` discovers
them) and reified property facts in the default graph. Firing sets
``life:firedAt``; the ``check_due`` poll is idempotent via
``FILTER NOT EXISTS { ?r life:firedAt ?f }``.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone

from pyoxigraph import Literal, NamedNode

from selma.memory import terms as core
from selma.memory.terms import uri as core_uri

from . import queries
from .exceptions import (ReminderNotFoundError, ReminderNotDueError,
                         ReminderSchedulerError)
from .models import Reminder
from .terms import PROPS, default_stated_by, instance


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _dt_literal(value: str) -> Literal:
    """Wrap an ISO datetime string as an xsd:dateTime Literal."""
    return Literal(value, datatype=NamedNode(core.XSD["dateTime"]))


class ReminderService:
    def __init__(self, memory, *, stated_by) -> None:
        if stated_by is None:
            stated_by = default_stated_by()
        self._mem = memory
        self._stated_by = stated_by
        self._timer: threading.Timer | None = None
        self._running = False
        self._lock = threading.Lock()

    # -- writes --
    def create(self, fire_at: str, *, about=None, label=None) -> str:
        u = instance("reminder")
        node = NamedNode(u)
        # Type assertion in the named graph so find() discovers it.
        self._mem.ask(
            f"INSERT DATA {{ GRAPH <{core_uri('default')}> "
            f"{{ <{u}> a <{core.uri('Reminder')}> }} }}")
        # Property facts in the default graph (reified).
        self._mem.remember(node, NamedNode(core.PROPS["validFrom"]),
                           _dt_literal(fire_at), stated_by=self._stated_by)
        if label is not None:
            self._mem.remember(node, NamedNode(core.PROPS["label"]),
                               Literal(label), stated_by=self._stated_by)
        if about is not None:
            if isinstance(about, str):
                about = NamedNode(about)
            self._mem.remember(node, NamedNode(PROPS["remindsAbout"]),
                               about, stated_by=self._stated_by)
        return u

    # -- reads --
    def _exists(self, u: str) -> bool:
        found = self._mem.find(core.uri("Reminder"))
        return any(f.value == u for f in found)

    def get(self, uri: str) -> Reminder:
        q = queries.reminder_get(uri)
        rows = list(self._mem.ask(q))
        if not rows:
            raise ReminderNotFoundError(uri)
        return Reminder.from_row(rows[0])

    def list(self, *, due_before=None, include_fired=False) -> list[Reminder]:
        q = queries.reminder_list(due_before=due_before,
                                  include_fired=include_fired)
        return [Reminder.from_row(r) for r in self._mem.ask(q)]

    # -- firing --
    def fire(self, uri: str, *, now: str | None = None) -> None:
        if not self._exists(uri):
            raise ReminderNotFoundError(uri)
        now = now or _now_iso()
        r = self.get(uri)
        if r.fired_at is not None:
            # Already fired: idempotent no-op.
            return
        if r.fire_at is not None and now < r.fire_at:
            raise ReminderNotDueError(
                f"{uri} fires at {r.fire_at}, now is {now}")
        self._mem.remember(NamedNode(uri), NamedNode(PROPS["firedAt"]),
                           _dt_literal(now), stated_by=self._stated_by)

    def check_due(self, *, now: str | None = None) -> list[str]:
        now = now or _now_iso()
        q = queries.reminder_check_due(now)
        due = [row["r"].value for row in self._mem.ask(q)]
        for u in due:
            self._mem.remember(NamedNode(u), NamedNode(PROPS["firedAt"]),
                               _dt_literal(now), stated_by=self._stated_by)
        return due

    # -- scheduler --
    def start(self, callback, *, interval: float = 30.0) -> None:
        with self._lock:
            if self._running:
                raise ReminderSchedulerError("scheduler already running")
            self._running = True
        self._arm(callback, interval)

    def _arm(self, callback, interval: float) -> None:
        """Schedule the next poll cycle on a daemon Timer."""
        with self._lock:
            if not self._running:
                return
            t = threading.Timer(interval, self._loop, args=(callback, interval))
            t.daemon = True
            self._timer = t
            t.start()

    def _loop(self, callback, interval: float) -> None:
        """One poll cycle: fire due reminders, dispatch, re-arm."""
        if not self._running:
            return
        try:
            for u in self.check_due():
                try:
                    callback(u)
                except Exception:
                    # Caller errors must not kill the loop.
                    pass
        except Exception:
            pass
        finally:
            if self._running:
                self._arm(callback, interval)

    def stop(self) -> None:
        with self._lock:
            self._running = False
            t = self._timer
            self._timer = None
        if t is not None:
            t.cancel()