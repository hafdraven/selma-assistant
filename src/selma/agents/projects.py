"""ProjectService — create, list, get projects (spec §4).

Projects are ``selma:Project`` instances stored via two memory calls: a type
assertion in the ``selma:default`` named graph (so ``find`` discovers them)
and reified property facts in the default graph.
"""
from __future__ import annotations

from pyoxigraph import Literal, NamedNode

from selma.memory import terms as core

from . import queries
from .exceptions import ProjectNotFoundError
from .models import Project
from .terms import default_stated_by, instance


class ProjectService:
    def __init__(self, memory, *, stated_by) -> None:
        if stated_by is None:
            stated_by = default_stated_by()
        self._mem = memory
        self._stated_by = stated_by

    # -- writes --
    def create(self, label: str, *, description=None, part_of=None) -> str:
        u = instance("project")
        node = NamedNode(u)
        # Type assertion in the named graph so find() discovers it.
        self._mem.ask(
            f"INSERT DATA {{ GRAPH <{core.uri('default')}> "
            f"{{ <{u}> a <{core.uri('Project')}> }} }}")
        self._mem.remember(node, NamedNode(core.PROPS["label"]),
                           Literal(label), stated_by=self._stated_by)
        if description is not None:
            self._mem.remember(node, NamedNode(core.PROPS["description"]),
                               Literal(description), stated_by=self._stated_by)
        if part_of is not None:
            if isinstance(part_of, str):
                part_of = NamedNode(part_of)
            self._mem.remember(node, NamedNode(core.PROPS["partOf"]),
                               part_of, stated_by=self._stated_by)
        return u

    # -- reads --
    def get(self, uri: str) -> Project:
        rows = list(self._mem.ask(queries.project_get(uri)))
        if not rows:
            raise ProjectNotFoundError(uri)
        p = Project.from_row(rows[0])
        return Project(uri=uri, label=p.label, description=p.description,
                       part_of=p.part_of)

    def list(self) -> list[Project]:
        rows = list(self._mem.ask(queries.project_list()))
        out = []
        for r in rows:
            p = Project.from_row(r)
            out.append(p)
        out.sort(key=lambda p: (p.label or "", p.uri))
        return out