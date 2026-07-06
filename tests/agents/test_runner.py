"""Tests for AgentRunner (spec §4, §6)."""
from __future__ import annotations

import pytest

from selma.agents.exceptions import TaskNotFoundError
from selma.memory.api import MemoryAPI


def test_run_success_completes_task(runner, tasks, projects):
    p = projects.create("P")
    u = tasks.create("A", project=p)

    def executor(task_uri: str, memory: MemoryAPI) -> str:
        return "did the work"

    result = runner.run(u, executor)
    assert result == "did the work"
    t = tasks.get(u)
    assert t.status == "done"
    assert t.completed_at is not None
    assert t.owned_by is not None
    assert t.execution_result == "did the work"


def test_run_claims_before_executing(runner, tasks, projects):
    p = projects.create("P")
    u = tasks.create("A", project=p)
    seen_status = {}

    def executor(task_uri: str, memory: MemoryAPI) -> str:
        seen_status["status"] = tasks.get(task_uri).status
        seen_status["owner"] = tasks.get(task_uri).owned_by
        return "ok"

    runner.run(u, executor)
    assert seen_status["status"] == "in_progress"
    assert seen_status["owner"] is not None


def test_run_failure_blocks_task(runner, tasks, projects):
    p = projects.create("P")
    u = tasks.create("A", project=p)

    def executor(task_uri: str, memory: MemoryAPI) -> str:
        raise RuntimeError("something broke")

    with pytest.raises(RuntimeError, match="something broke"):
        runner.run(u, executor)
    t = tasks.get(u)
    assert t.status == "blocked"
    assert t.block_reason is not None
    assert "something broke" in t.block_reason


def test_run_passes_task_uri_and_memory(runner, tasks, projects):
    p = projects.create("P")
    u = tasks.create("A", project=p)
    received = {}

    def executor(task_uri: str, memory: MemoryAPI) -> str:
        received["uri"] = task_uri
        received["memory"] = memory
        return "ok"

    runner.run(u, executor)
    assert received["uri"] == u
    assert received["memory"] is not None


def test_run_unknown_task_raises(runner):
    def executor(task_uri: str, memory: MemoryAPI) -> str:
        return "ok"

    with pytest.raises(TaskNotFoundError):
        runner.run("https://selma.example/ns/agents#task/nope", executor)


def test_run_on_already_in_progress(runner, tasks, projects):
    p = projects.create("P")
    u = tasks.create("A", project=p)
    tasks.set_status(u, "in_progress")
    tasks.set_owner(u, "https://ex/other")

    def executor(task_uri: str, memory: MemoryAPI) -> str:
        return "ok"

    runner.run(u, executor)
    t = tasks.get(u)
    assert t.status == "done"


def test_run_on_done_task_raises(runner, tasks, projects):
    p = projects.create("P")
    u = tasks.create("A", project=p)
    tasks.set_status(u, "in_progress")
    tasks.set_status(u, "done")

    def executor(task_uri: str, memory: MemoryAPI) -> str:
        return "ok"

    with pytest.raises(Exception):
        runner.run(u, executor)