"""Tests for TaskCoordinator (spec §4)."""
from __future__ import annotations

import pytest

from selma.agents.exceptions import (InvalidStatusTransitionError,
                                     TaskNotFoundError)


def test_open_tasks_lists_open_only(coordinator, tasks, projects):
    p = projects.create("P")
    a = tasks.create("A", project=p, due_by="2026-07-10T17:00:00")
    b = tasks.create("B", project=p, due_by="2026-07-09T17:00:00")
    tasks.create("C", project=p)  # no due
    # Complete one; it should drop out of open.
    tasks.set_status(a, "in_progress")
    tasks.set_status(a, "done")
    open_uris = [t.uri for t in coordinator.open_tasks(p)]
    assert a not in open_uris
    assert b in open_uris


def test_open_tasks_sorted_by_deadline(coordinator, tasks, projects):
    p = projects.create("P")
    later = tasks.create("Later", project=p, due_by="2026-07-10T17:00:00")
    sooner = tasks.create("Sooner", project=p, due_by="2026-07-08T17:00:00")
    nodeadline = tasks.create("NoDeadline", project=p)
    open_uris = [t.uri for t in coordinator.open_tasks(p)]
    # Sooner first, then later, no-deadline last.
    assert open_uris[0] == sooner
    assert open_uris[1] == later
    assert open_uris[2] == nodeadline


def test_claim_sets_status_and_owner(coordinator, tasks, projects, agent_uri):
    p = projects.create("P")
    u = tasks.create("A", project=p)
    coordinator.claim(u, owner=agent_uri)
    t = tasks.get(u)
    assert t.status == "in_progress"
    assert t.owned_by == agent_uri


def test_claim_unknown_raises(coordinator):
    with pytest.raises(TaskNotFoundError):
        coordinator.claim("https://selma.example/ns/agents#task/nope",
                          owner="https://ex/a")


def test_complete_sets_status_and_completed_at(coordinator, tasks, projects):
    p = projects.create("P")
    u = tasks.create("A", project=p)
    coordinator.claim(u, owner="https://ex/a")
    coordinator.complete(u)
    t = tasks.get(u)
    assert t.status == "done"
    assert t.completed_at is not None


def test_complete_unknown_raises(coordinator):
    with pytest.raises(TaskNotFoundError):
        coordinator.complete("https://selma.example/ns/agents#task/nope")


def test_block_sets_status_and_reason(coordinator, tasks, projects):
    p = projects.create("P")
    u = tasks.create("A", project=p)
    coordinator.claim(u, owner="https://ex/a")
    coordinator.block(u, reason="Waiting on vendor")
    t = tasks.get(u)
    assert t.status == "blocked"
    assert t.block_reason == "Waiting on vendor"


def test_block_unknown_raises(coordinator):
    with pytest.raises(TaskNotFoundError):
        coordinator.block("https://selma.example/ns/agents#task/nope",
                          reason="x")


def test_blocked_tasks_lists_blocked(coordinator, tasks, projects):
    p = projects.create("P")
    a = tasks.create("A", project=p)
    b = tasks.create("B", project=p)
    coordinator.block(a, reason="r1")
    blocked = [t.uri for t in coordinator.blocked_tasks(project=p)]
    assert blocked == [a]
    assert b not in blocked


def test_blocked_tasks_no_project_filter(coordinator, tasks, projects):
    p1 = projects.create("P1")
    p2 = projects.create("P2")
    a = tasks.create("A", project=p1)
    b = tasks.create("B", project=p2)
    coordinator.block(a, reason="r1")
    coordinator.block(b, reason="r2")
    blocked = {t.uri for t in coordinator.blocked_tasks()}
    assert blocked == {a, b}


def test_blockers_returns_undone_dependencies(coordinator, tasks, projects):
    p = projects.create("P")
    a = tasks.create("A", project=p)
    b = tasks.create("B", project=p)
    tasks.add_dependency(b, a)
    # A is still open, so it blocks B.
    blockers = coordinator.blockers(b)
    assert a in blockers


def test_blockers_excludes_done_dependencies(coordinator, tasks, projects):
    p = projects.create("P")
    a = tasks.create("A", project=p)
    b = tasks.create("B", project=p)
    tasks.add_dependency(b, a)
    tasks.set_status(a, "in_progress")
    tasks.set_status(a, "done")
    blockers = coordinator.blockers(b)
    assert blockers == []


def test_blockers_no_dependencies(coordinator, tasks, projects):
    p = projects.create("P")
    a = tasks.create("A", project=p)
    assert coordinator.blockers(a) == []