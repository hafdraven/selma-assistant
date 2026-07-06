"""AgentRunner — autonomous task execution (spec §4, §6).

An ``AgentRunner`` takes a task and an executor callable, claims the task,
runs the executor, records the outcome in memory, and updates the task status.
v1 is sequential (one task at a time per ``run`` call); there is no parallelism
and no persistent queue.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from pyoxigraph import Literal, NamedNode

from selma.memory import terms as core
from selma.memory.api import MemoryAPI

from .exceptions import TaskNotClaimableError
from .tasks import TaskService
from .terms import AGENT_SELF, PROPS, default_stated_by


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class AgentRunner:
    def __init__(self, memory: MemoryAPI, *, agent: str = AGENT_SELF,
                 stated_by=None) -> None:
        if stated_by is None:
            stated_by = default_stated_by()
        self._mem = memory
        self._agent = agent
        self._stated_by = stated_by
        self._tasks = TaskService(memory, stated_by=stated_by)

    def run(self, task_uri: str,
            executor: Callable[[str, MemoryAPI], str]) -> str:
        """Claim `task_uri`, run `executor`, record the outcome, and update
        the task status.

        On success the task is completed (status -> done, completedAt -> now)
        and ``agents:executionResult`` is set to the executor's return value,
        which is also returned. On exception the task is blocked (status ->
        blocked, ``agents:blockReason`` <- exception message) and the
        exception is re-raised.
        """
        t = self._tasks.get(task_uri)
        if t.status not in ("open", "in_progress"):
            raise TaskNotClaimableError(
                f"task {task_uri} is in '{t.status}' state and cannot be run")

        # Claim: status -> in_progress, ownedBy -> agent.
        self._tasks.set_status(task_uri, "in_progress")
        self._tasks.set_owner(task_uri, self._agent)

        try:
            result = executor(task_uri, self._mem)
        except Exception as exc:
            # Block the task and record the reason.
            self._tasks.set_status(task_uri, "blocked")
            self._mem.remember(NamedNode(task_uri),
                               NamedNode(PROPS["blockReason"]),
                               Literal(str(exc)), stated_by=self._stated_by)
            raise

        # Success: store the result and complete.
        self._mem.remember(NamedNode(task_uri),
                           NamedNode(PROPS["executionResult"]),
                           Literal(result), stated_by=self._stated_by)
        self._tasks.set_status(task_uri, "done")
        now = _now_iso()
        from .tasks import _dt_literal
        self._mem.remember(NamedNode(task_uri),
                           NamedNode(core.PROPS["completedAt"]),
                           _dt_literal(now), stated_by=self._stated_by)
        return result