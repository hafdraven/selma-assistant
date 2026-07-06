"""Tests for TaskService (spec §4)."""
from __future__ import annotations

import pytest

from selma.agents.exceptions import TaskNotFoundError
from selma.agents.models import Task
from selma.memory import terms


def test_create_persists_task(tasks, fresh_api):
    u = tasks.create("Write draft", description="First pass")
    found = fresh_api.find(terms.uri("Task"))
    assert u in [f.value for f in found]


def test_create_default_status_open(tasks):
    u = tasks.create("Write draft")
    t = tasks.get(u)
    assert t.status == "open"


def test_create_stores_label_description(tasks):
    u = tasks.create("Write draft", description="First pass")
    t = tasks.get(u)
    assert t.label == "Write draft"
    assert t.description == "First pass"


def test_create_with_project_owner_due(tasks, projects):
    p = projects.create("Website")
    owner = "https://selma.example/ns/core#self"
    u = tasks.create("Task", project=p, owner=owner,
                     due_by="2026-07-10T17:00:00")
    t = tasks.get(u)
    assert t.part_of == p
    assert t.owned_by == owner
    assert t.due_by == "2026-07-10T17:00:00"


def test_get_unknown_raises(tasks):
    with pytest.raises(TaskNotFoundError):
        tasks.get("https://selma.example/ns/agents#task/nope")


def test_list_returns_tasks(tasks):
    a = tasks.create("A")
    b = tasks.create("B")
    items = tasks.list()
    assert {a, b} == {t.uri for t in items}


def test_list_filtered_by_project(tasks, projects):
    p1 = projects.create("P1")
    p2 = projects.create("P2")
    a = tasks.create("A", project=p1)
    b = tasks.create("B", project=p2)
    c = tasks.create("C", project=p1)
    in_p1 = tasks.list(project=p1)
    assert {t.uri for t in in_p1} == {a, c}
    in_p2 = tasks.list(project=p2)
    assert {t.uri for t in in_p2} == {b}


def test_set_status_uses_soft_forget_preserving_history(tasks, fresh_api):
    from pyoxigraph import NamedNode
    u = tasks.create("A")
    tasks.set_status(u, "in_progress")
    t = tasks.get(u)
    assert t.status == "in_progress"
    # History: the old "open" fact should still exist (with a validTo), while
    # the current "in_progress" fact has no validTo. Query history via recall
    # on the subject alone (recall's subject+predicate filter does not apply)
    # and filter in Python.
    rows = fresh_api.recall(NamedNode(u), include_history=True)
    statuses = sorted(r["o"].value for r in rows
                      if r["p"].value == "https://selma.example/ns/core#hasStatus")
    assert statuses == ["in_progress", "open"]


def test_set_owner_uses_supersede(tasks):
    u = tasks.create("A")
    tasks.set_owner(u, "https://ex/agent1")
    t = tasks.get(u)
    assert t.owned_by == "https://ex/agent1"
    tasks.set_owner(u, "https://ex/agent2")
    t = tasks.get(u)
    assert t.owned_by == "https://ex/agent2"


def test_add_dependency_and_query(tasks):
    a = tasks.create("A")
    b = tasks.create("B")
    tasks.add_dependency(b, a)
    deps = tasks.dependencies(b)
    assert deps == [a]
    # A does not depend on B.
    assert tasks.dependencies(a) == []


def test_get_returns_task_instance(tasks):
    u = tasks.create("A")
    t = tasks.get(u)
    assert isinstance(t, Task)
    assert t.uri == u


def test_task_is_frozen(tasks):
    u = tasks.create("A")
    t = tasks.get(u)
    with pytest.raises(Exception):
        t.status = "done"