"""TaskService — create, list, get, and mutate tasks (spec §4).

Tasks are ``selma:Task`` instances stored via two memory calls: a type
assertion in the ``selma:default`` named graph (so ``find`` discovers them)
and reified property facts in the default graph. Single-valued lifecycle
facts (``hasStatus``, ``ownedBy``) are mutated with ``supersede`` so the old
value is retired (``validTo = now``) and history is preserved.
"""
from __future__ import annotations

from pyoxigraph import Literal, NamedNode

from selma.memory import terms as core

from . import queries
from .exceptions import TaskNotFoundError
from .models import Task
from .terms import default_stated_by, instance


def _dt_literal(value: str) -> Literal:
    """Wrap an ISO datetime string as an xsd:dateTime Literal."""
    return Literal(value, datatype=NamedNode(core.XSD["dateTime"]))


class TaskService:
    def __init__(self, memory, *, stated_by) -> None:
        if stated_by is None:
            stated_by = default_stated_by()
        self._mem = memory
        self._stated_by = stated_by

    # -- writes --
    def create(self, label: str, *, project=None, description=None,
               owner=None, due_by=None, depends_on=None) -> str:
        u = instance("task")
        node = NamedNode(u)
        # Type assertion in the named graph so find() discovers it.
        self._mem.ask(
            f"INSERT DATA {{ GRAPH <{core.uri('default')}> "
            f"{{ <{u}> a <{core.uri('Task')}> }} }}")
        self._mem.remember(node, NamedNode(core.PROPS["label"]),
                           Literal(label), stated_by=self._stated_by)
        if description is not None:
            self._mem.remember(node, NamedNode(core.PROPS["description"]),
                               Literal(description), stated_by=self._stated_by)
        # New tasks start in the 'open' status.
        self._mem.remember(node, NamedNode(core.PROPS["hasStatus"]),
                           Literal("open"), stated_by=self._stated_by)
        if owner is not None:
            if isinstance(owner, str):
                owner = NamedNode(owner)
            self._mem.remember(node, NamedNode(core.PROPS["ownedBy"]),
                               owner, stated_by=self._stated_by)
        if due_by is not None:
            self._mem.remember(node, NamedNode(core.PROPS["dueBy"]),
                               _dt_literal(due_by), stated_by=self._stated_by)
        if project is not None:
            if isinstance(project, str):
                project = NamedNode(project)
            self._mem.remember(node, NamedNode(core.PROPS["partOf"]),
                               project, stated_by=self._stated_by)
        if depends_on is not None:
            if isinstance(depends_on, str):
                depends_on = NamedNode(depends_on)
            self._mem.remember(node, NamedNode(core.PROPS["dependsOn"]),
                               depends_on, stated_by=self._stated_by)
        return u

    # -- mutations --
    def set_status(self, uri: str, status: str) -> None:
        """Retire the current hasStatus fact (soft) and assert a fresh one.

        Uses ``forget(soft=True)`` + ``remember`` rather than ``supersede``
        because ``supersede`` is ambiguous for multi-fact subjects: it picks
        the first fact's predicate regardless of which predicate you intend
        to retire, and refuses once any fact about the subject has a
        ``validTo``. The soft-forget pattern preserves history (the old fact
        keeps its ``validTo = now``) while inserting a current replacement.
        """
        node = NamedNode(uri)
        self._mem.forget(subject=node,
                         predicate=NamedNode(core.PROPS["hasStatus"]),
                         soft=True)
        self._mem.remember(node, NamedNode(core.PROPS["hasStatus"]),
                           Literal(status), stated_by=self._stated_by)

    def set_owner(self, uri: str, owner: str) -> None:
        """Retire the current ownedBy fact (soft) and assert a fresh one."""
        node = NamedNode(uri)
        if isinstance(owner, str):
            owner = NamedNode(owner)
        self._mem.forget(subject=node,
                         predicate=NamedNode(core.PROPS["ownedBy"]),
                         soft=True)
        self._mem.remember(node, NamedNode(core.PROPS["ownedBy"]),
                           owner, stated_by=self._stated_by)

    def add_dependency(self, uri: str, depends_on: str) -> None:
        """Assert a dependsOn link from `uri` to `depends_on`."""
        if isinstance(depends_on, str):
            depends_on = NamedNode(depends_on)
        self._mem.remember(NamedNode(uri), NamedNode(core.PROPS["dependsOn"]),
                           depends_on, stated_by=self._stated_by)

    # -- reads --
    def get(self, uri: str) -> Task:
        rows = list(self._mem.ask(queries.task_get(uri)))
        if not rows:
            raise TaskNotFoundError(uri)
        t = Task.from_row(rows[0])
        return Task(uri=uri, label=t.label, description=t.description,
                    status=t.status, owned_by=t.owned_by, due_by=t.due_by,
                    completed_at=t.completed_at, part_of=t.part_of,
                    block_reason=t.block_reason,
                    execution_result=t.execution_result)

    def list(self, *, project=None) -> list[Task]:
        rows = list(self._mem.ask(queries.task_list(project=project)))
        out = []
        for r in rows:
            t = Task.from_row(r)
            out.append(t)
        out.sort(key=lambda t: (t.label or "", t.uri))
        return out

    def dependencies(self, uri: str) -> list[str]:
        rows = list(self._mem.ask(queries.task_dependencies(uri)))
        return [row["dep"].value for row in rows]