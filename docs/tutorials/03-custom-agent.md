# Tutorial 3: Custom Agent

The `selma.agents` sub-project provides projects, tasks, coordination, and
autonomous execution. This tutorial walks through the full lifecycle: setting
up the `AgentsAssistant`, creating a project with dependent tasks, writing an
executor function, running it through the `AgentRunner`, and verifying the
status transitions and recorded result.

> **Prerequisites**: Install Selma with `pip install -e ".[dev]"`. See the
> [getting-started guide](../getting-started.md) if you have not done this yet.

## What you will build

A script that:

1. Creates an `AgentsAssistant` over an in-memory store.
2. Creates a project and three tasks with a dependency chain.
3. Lists open tasks for the project.
4. Writes an executor function that does work and returns a result string.
5. Runs the `AgentRunner` on each task in dependency order.
6. Verifies the status transitions (`open → in_progress → done`) and the
   recorded `agents:executionResult`.

## Step 1 — Set up the AgentsAssistant

`AgentsAssistant` is a thin facade over four services: `ProjectService`,
`TaskService`, `TaskCoordinator`, and `AgentRunner`. All share the same
`MemoryAPI` and `stated_by` provenance agent.

```python
from selma.memory import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph
from selma.agents import AgentsAssistant

memory = MemoryAPI(EmbeddedOxigraph())
agents = AgentsAssistant(memory)
```

## Step 2 — Create a project

A project is a `selma:Project` with a label, optional description, and optional
`partOf` (for sub-projects). `create` returns the project URI.

```python
project_uri = agents.projects.create(
    "website",
    description="Personal website rebuild",
)
print("project:", project_uri)
```

Verify it was stored:

```python
project = agents.projects.get(project_uri)
print("label:", project.label)
print("description:", project.description)
```

## Step 3 — Add tasks with dependencies

Tasks are `selma:Task` instances. New tasks start in the `open` status. You can
set `project`, `due_by`, `owner`, and `depends_on` at creation time, and add
dependencies later with `add_dependency`.

Create three tasks that form a dependency chain: "write outline" → "write draft"
→ "publish". The draft depends on the outline, and publish depends on the draft.

```python
task_outline = agents.tasks.create(
    "Write outline",
    project=project_uri,
    due_by="2026-07-10T17:00:00",
)
task_draft = agents.tasks.create(
    "Write draft",
    project=project_uri,
    due_by="2026-07-12T17:00:00",
    depends_on=task_outline,
)
task_publish = agents.tasks.create(
    "Publish",
    project=project_uri,
    due_by="2026-07-14T17:00:00",
    depends_on=task_draft,
)
print("outline:", task_outline)
print("draft:", task_draft)
print("publish:", task_publish)
```

Verify the dependency links:

```python
print("draft deps:", agents.tasks.dependencies(task_draft))
# ['https://selma.example/ns/agents#task/...']
print("publish deps:", agents.tasks.dependencies(task_publish))
# ['https://selma.example/ns/agents#task/...']
```

## Step 4 — List open tasks

`TaskCoordinator.open_tasks(project)` returns all tasks in the `open` or
`in_progress` status for a project, sorted by deadline (earliest first; tasks
without a deadline sort last).

```python
print("=== Open tasks ===")
for t in agents.coordinator.open_tasks(project_uri):
    print(f"  [{t.status}] {t.label} (due: {t.due_by})")
```

Output:

```
  [open] Write outline (due: 2026-07-10T17:00:00)
  [open] Write draft (due: 2026-07-12T17:00:00)
  [open] Publish (due: 2026-07-14T17:00:00)
```

You can also check which tasks are blocked by incomplete dependencies using
`coordinator.blockers(uri)`:

```python
print("publish blockers:", agents.coordinator.blockers(task_publish))
# ['https://selma.example/ns/agents#task/...']  (the draft, not yet done)
```

## Step 5 — Write an executor function

The `AgentRunner.run` method takes a `task_uri` and an `executor` callable with
the signature `executor(task_uri: str, memory: MemoryAPI) -> str`. The executor
does the actual work and returns a result string. On success, the runner
records the return value as `agents:executionResult` and marks the task `done`.
On exception, the runner marks the task `blocked` with the error message and
re-raises.

The executor receives the `MemoryAPI` instance so it can read and write facts
during execution — for example, looking up task dependencies or storing
intermediate results.

```python
def my_executor(task_uri: str, memory: MemoryAPI) -> str:
    """A simple executor that 'does work' and returns a summary."""
    # In a real agent this could call an LLM, run a build, send an email, etc.
    # Here we just look up the task label and return a mock result.
    task = agents.tasks.get(task_uri)
    label = task.label or task_uri
    return f"completed: {label}"
```

## Step 6 — Run the AgentRunner

The runner processes one task per `run` call (v1 is sequential — no
parallelism, no persistent queue). Run tasks in dependency order: outline first,
then draft, then publish.

```python
# Run the outline task.
result1 = agents.runner.run(task_outline, my_executor)
print("result1:", result1)
# result1: completed: Write outline

# Now the draft's blocker is done — run it.
result2 = agents.runner.run(task_draft, my_executor)
print("result2:", result2)
# result2: completed: Write draft

# Finally, publish.
result3 = agents.runner.run(task_publish, my_executor)
print("result3:", result3)
# result3: completed: Publish
```

## Step 7 — Verify status transitions and execution result

After running, each task should be in the `done` status with a `completedAt`
timestamp and an `agents:executionResult` fact. Fetch each task and check:

```python
print("=== Final status ===")
for t in agents.tasks.list(project=project_uri):
    print(f"  [{t.status}] {t.label}")
    print(f"    completed_at: {t.completed_at}")
    print(f"    execution_result: {t.execution_result}")
```

Output:

```
  [done] Publish
    completed_at: 2026-07-11T...
    execution_result: completed: Publish
  [done] Write draft
    completed_at: 2026-07-11T...
    execution_result: completed: Write draft
  [done] Write outline
    completed_at: 2026-07-11T...
    execution_result: completed: Write outline
```

Confirm the blockers are now cleared (the coordinator returns only non-done
dependencies):

```python
print("publish blockers (after all done):",
      agents.coordinator.blockers(task_publish))
# []
```

The `open_tasks` list should now be empty:

```python
print("open tasks:", agents.coordinator.open_tasks(project_uri))
# []
```

## What happens inside run()

When you call `agents.runner.run(task_uri, executor)`:

1. **Claim**: `set_status(task_uri, "in_progress")` and
   `set_owner(task_uri, self._agent)`. The old `open` status fact is
   soft-deleted (retains history).
2. **Execute**: calls `executor(task_uri, self._mem)`.
3. **On success**: stores `agents:executionResult` as a reified fact, sets
   status to `done`, and sets `completedAt` to now.
4. **On exception**: sets status to `blocked`, stores `agents:blockReason`
   with the exception message, and re-raises.

The status transition table enforced by `TaskCoordinator` is:

```
open → in_progress | blocked
in_progress → done | blocked
blocked → in_progress | open
done → (terminal)
```

## Handling executor failures

If your executor raises an exception, the runner blocks the task and re-raises.
You can catch the exception and inspect the blocked task:

```python
failing_task = agents.tasks.create("failing task", project=project_uri)

def bad_executor(task_uri, memory):
    raise RuntimeError("something broke")

try:
    agents.runner.run(failing_task, bad_executor)
except RuntimeError as e:
    print("executor failed:", e)

blocked = agents.tasks.get(failing_task)
print("status:", blocked.status)           # blocked
print("block_reason:", blocked.block_reason)  # something broke
```

A blocked task can be unblocked by moving it back to `open` with
`tasks.set_status`, then run again with a fixed executor:

```python
# Move the blocked task back to open so the runner can claim it.
agents.tasks.set_status(failing_task, "open")
# Run with a working executor — the runner claims it (open -> in_progress)
# and completes it on success.
agents.runner.run(failing_task, my_executor)
print("status after retry:", agents.tasks.get(failing_task).status)
# done
```

## Complete runnable script

Save as `custom_agent_tutorial.py` and run with `python custom_agent_tutorial.py`.

```python
"""Tutorial 3: writing a custom autonomous agent."""
from __future__ import annotations

from selma.memory import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph
from selma.agents import AgentsAssistant


# -- Executor ----------------------------------------------------------------

def my_executor(task_uri: str, memory: MemoryAPI) -> str:
    """A simple executor: look up the task label and return a summary.

    In a real agent this could call an LLM, run a build, send an email,
    or do anything else.  The executor receives the MemoryAPI instance
    so it can read and write facts during execution.
    """
    task = agents.tasks.get(task_uri)
    label = task.label or task_uri
    return f"completed: {label}"


def bad_executor(task_uri: str, memory: MemoryAPI) -> str:
    """An executor that always fails, to demonstrate blocking."""
    raise RuntimeError("something broke")


# -- Main --------------------------------------------------------------------

def main() -> None:
    # 1. Set up the AgentsAssistant.
    global agents
    memory = MemoryAPI(EmbeddedOxigraph())
    agents = AgentsAssistant(memory)
    print("=== AgentsAssistant ready ===")
    print(agents.describe())

    # 2. Create a project.
    project_uri = agents.projects.create(
        "website",
        description="Personal website rebuild",
    )
    print("\n=== Project ===")
    project = agents.projects.get(project_uri)
    print(f"  {project.label}: {project.description}")

    # 3. Create tasks with a dependency chain: outline → draft → publish.
    task_outline = agents.tasks.create(
        "Write outline",
        project=project_uri,
        due_by="2026-07-10T17:00:00",
    )
    task_draft = agents.tasks.create(
        "Write draft",
        project=project_uri,
        due_by="2026-07-12T17:00:00",
        depends_on=task_outline,
    )
    task_publish = agents.tasks.create(
        "Publish",
        project=project_uri,
        due_by="2026-07-14T17:00:00",
        depends_on=task_draft,
    )
    print("\n=== Tasks created ===")
    print("  outline:", task_outline)
    print("  draft:", task_draft)
    print("  publish:", task_publish)

    # 4. List open tasks.
    print("\n=== Open tasks ===")
    for t in agents.coordinator.open_tasks(project_uri):
        print(f"  [{t.status}] {t.label} (due: {t.due_by})")

    print("  publish blockers:", agents.coordinator.blockers(task_publish))

    # 5. Run the executor on each task in dependency order.
    print("\n=== Running tasks ===")
    for uri in (task_outline, task_draft, task_publish):
        result = agents.runner.run(uri, my_executor)
        t = agents.tasks.get(uri)
        print(f"  {t.label}: {result}  [status={t.status}]")

    # 6. Verify final status and execution results.
    print("\n=== Final status ===")
    for t in agents.tasks.list(project=project_uri):
        print(f"  [{t.status}] {t.label}")
        print(f"    completed_at: {t.completed_at}")
        print(f"    execution_result: {t.execution_result}")

    print("\n  open tasks:", agents.coordinator.open_tasks(project_uri))
    print("  publish blockers (after all done):",
          agents.coordinator.blockers(task_publish))

    # 7. Demonstrate executor failure and blocking.
    print("\n=== Failure handling ===")
    failing_task = agents.tasks.create("failing task", project=project_uri)
    try:
        agents.runner.run(failing_task, bad_executor)
    except RuntimeError as e:
        print("  executor raised:", e)
    blocked = agents.tasks.get(failing_task)
    print(f"  status: {blocked.status}")          # blocked
    print(f"  block_reason: {blocked.block_reason}")  # something broke

    # 8. Retry the blocked task with a working executor.
    print("\n=== Retry ===")
    # Move the blocked task back to open so the runner can claim it.
    agents.tasks.set_status(failing_task, "open")
    agents.runner.run(failing_task, my_executor)
    retried = agents.tasks.get(failing_task)
    print(f"  status after retry: {retried.status}")  # done
    print(f"  execution_result: {retried.execution_result}")

    print("\nDone.")


if __name__ == "__main__":
    main()
```

## Next steps

- [Agents API reference](../api-reference/agents.md) — full method signatures for
  `ProjectService`, `TaskService`, `TaskCoordinator`, and `AgentRunner`.
- [Architecture overview](../architecture.md) — how `selma.agents` fits into the
  platform.
- [Voice commands cheat sheet](../voice-commands.md) — trigger tasks and list
  them via voice using `CreateTaskIntent` and `ListTasksIntent`.