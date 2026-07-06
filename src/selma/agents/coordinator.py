"""TaskCoordinator — claim, complete, block, and inspect tasks (spec §4).

A coordination layer over ``TaskService`` that enforces status transitions and
provides project-scoped views (open tasks sorted by deadline, blocked tasks
and their blockers). Status and owner mutations use ``TaskService.set_status``
/ ``set_owner`` (which ``supersede`` the old facts, preserving history).
"""
from __future__ import annotations

from datetime import datetime, timezone

from pyoxigraph import Literal, NamedNode

from selma.memory import terms as core

from . import queries
from .exceptions import (InvalidStatusTransitionError, TaskNotFoundError)
from .models import Task, _row_get
from .tasks import TaskService
from .terms import PROPS, default_stated_by


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# Allowed status transitions (from -> set of permitted targets).
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "open": {"in_progress", "blocked"},
    "in_progress": {"done", "blocked"},
    "blocked": {"in_progress", "open"},
    "done": set(),
}


class TaskCoordinator:
    def __init__(self, memory, *, stated_by) -> None:
        if stated_by is None:
            stated_by = default_stated_by()
        self._mem = memory
        self._stated_by = stated_by
        self._tasks = TaskService(memory, stated_by=stated_by)

    # -- views --
    def open_tasks(self, project: str) -> list[Task]:
        """Open/in_progress tasks for a project, sorted by deadline (earliest
        first; tasks with no deadline last)."""
        all_tasks = self._tasks.list(project=project)
        open_ = [t for t in all_tasks if t.status in ("open", "in_progress")]
        # Stable sort: tasks with a due_by come first (by due_by), then those
        # without. Tasks without due_by sort by label for determinism.
        open_.sort(key=lambda t: (t.due_by is None, t.due_by or "", t.uri))
        return open_

    def blocked_tasks(self, *, project=None) -> list[Task]:
        rows = list(self._mem.ask(queries.blocked_tasks(project=project)))
        out = []
        for r in rows:
            label = _row_get(r, "label")
            part = _row_get(r, "part")
            blockreason = _row_get(r, "blockreason")
            owner = _row_get(r, "owner")
            out.append(Task(
                uri=r["uri"].value,
                label=label.value if label is not None else None,
                status="blocked",
                part_of=part.value if part is not None else None,
                block_reason=(blockreason.value
                              if blockreason is not None else None),
                owned_by=owner.value if owner is not None else None,
            ))
        out.sort(key=lambda t: (t.label or "", t.uri))
        return out

    def blockers(self, uri: str) -> list[str]:
        """List dependsOn targets of `uri` that are not done."""
        rows = list(self._mem.ask(queries.task_blockers(uri)))
        return [row["dep"].value for row in rows]

    # -- mutations --
    def claim(self, uri: str, *, owner: str) -> None:
        """Set status to in_progress and ownedBy to the claiming agent."""
        t = self._tasks.get(uri)
        if t.status not in ("open", "in_progress"):
            raise InvalidStatusTransitionError(
                f"cannot claim task in '{t.status}' state")
        self._tasks.set_status(uri, "in_progress")
        self._tasks.set_owner(uri, owner)

    def complete(self, uri: str) -> None:
        """Set status to done and completedAt to now."""
        t = self._tasks.get(uri)
        if t.status not in ("in_progress", "open"):
            raise InvalidStatusTransitionError(
                f"cannot complete task in '{t.status}' state")
        self._tasks.set_status(uri, "done")
        now = _now_iso()
        from .tasks import _dt_literal
        self._mem.remember(NamedNode(uri), NamedNode(core.PROPS["completedAt"]),
                           _dt_literal(now), stated_by=self._stated_by)

    def block(self, uri: str, *, reason: str) -> None:
        """Set status to blocked and store the block reason as a fact."""
        t = self._tasks.get(uri)
        if t.status not in ("open", "in_progress", "blocked"):
            raise InvalidStatusTransitionError(
                f"cannot block task in '{t.status}' state")
        if t.status != "blocked":
            self._tasks.set_status(uri, "blocked")
        # Record the reason as a fresh agents:blockReason fact.
        self._mem.remember(NamedNode(uri), NamedNode(PROPS["blockReason"]),
                           Literal(reason), stated_by=self._stated_by)