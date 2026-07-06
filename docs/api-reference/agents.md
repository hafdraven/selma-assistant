# `selma.agents` API reference

`selma.agents` is the autonomous-task-execution and project-coordination core.
It is a pure client of `selma.memory` — projects and tasks are stored as
reified facts through `MemoryAPI`. The public surface is four services plus a
thin `AgentsAssistant` facade and two frozen dataclasses.

## Public exports

| Name | Kind | Description |
|------|------|-------------|
| `AgentsAssistant` | class | Facade over the four agents services. |
| `ProjectService` | class | Create, list, and get projects. |
| `TaskService` | class | Create, list, get, and mutate tasks. |
| `TaskCoordinator` | class | Claim, complete, block, and inspect tasks. |
| `AgentRunner` | class | Autonomous task execution (sequential, single task). |
| `Project` | dataclass | A `selma:Project` with label, description, optional `partOf`. |
| `Task` | dataclass | A `selma:Task` with lifecycle and coordination properties. |
| `AgentsError` | exception | Base class for all `selma.agents` errors. |
| `ProjectNotFoundError` | exception | A project URI was not found in memory. |
| `TaskNotFoundError` | exception | A task URI was not found in memory. |
| `InvalidStatusTransitionError` | exception | A disallowed status transition was requested. |
| `TaskNotClaimableError` | exception | `run` called on a task not in an open/in_progress state. |

## `AgentsAssistant`

```python
AgentsAssistant(memory, *, stated_by=None, agent: str = AGENT_SELF) -> None
```

Thin facade over `ProjectService`, `TaskService`, `TaskCoordinator`, and
`AgentRunner`, all sharing the same `memory` (`MemoryAPI`) and `stated_by`
provenance agent. `agent` identifies the runner (default `AGENT_SELF`).

| Member | Signature | Returns |
|--------|-----------|---------|
| `projects` | property | `ProjectService` |
| `tasks` | property | `TaskService` |
| `coordinator` | property | `TaskCoordinator` |
| `runner` | property | `AgentRunner` |
| `describe` | `describe() -> dict` | compact surface description |

### Example

```python
from selma.memory import MemoryAPI, EmbeddedOxigraph
from selma.agents import AgentsAssistant

agents = AgentsAssistant(MemoryAPI(EmbeddedOxigraph()))
p = agents.projects.create("docs", description="user docs")
t = agents.tasks.create("write memory ref", project=p)
agents.coordinator.claim(t, owner="https://selma.example/ns/core#self")
agents.coordinator.complete(t)
print([tk.label for tk in agents.tasks.list(project=p)])
```

## `ProjectService`

```python
ProjectService(memory, *, stated_by) -> None
```

Projects are `selma:Project` instances: a type assertion in the
`selma:default` named graph plus reified property facts.

| Method | Signature | Returns | Raises |
|--------|-----------|---------|--------|
| `create` | `create(label: str, *, description=None, part_of=None) -> str` | project URI | — |
| `get` | `get(uri: str) -> Project` | `Project` | `ProjectNotFoundError` |
| `list` | `list() -> list[Project]` | list (sorted by label, uri) | — |

### Example

```python
from selma.memory import MemoryAPI, EmbeddedOxigraph
from selma.agents import ProjectService

ps = ProjectService(MemoryAPI(EmbeddedOxigraph()), stated_by="https://selma.example/ns/core#self")
u = ps.create("docs", description="user docs")
print(ps.get(u))          # Project(uri=u, label="docs", description="user docs")
print([p.label for p in ps.list()])
```

## `TaskService`

```python
TaskService(memory, *, stated_by) -> None
```

Tasks are `selma:Task` instances. New tasks start in the `open` status.
Single-valued lifecycle facts (`hasStatus`, `ownedBy`) are mutated with
`forget(soft=True)` + a fresh `remember` so the full history is retained.

| Method | Signature | Returns | Raises |
|--------|-----------|---------|--------|
| `create` | `create(label: str, *, project=None, description=None, owner=None, due_by=None, depends_on=None) -> str` | task URI | — |
| `set_status` | `set_status(uri: str, status: str) -> None` | — | — |
| `set_owner` | `set_owner(uri: str, owner: str) -> None` | — | — |
| `add_dependency` | `add_dependency(uri: str, depends_on: str) -> None` | — | — |
| `get` | `get(uri: str) -> Task` | `Task` | `TaskNotFoundError` |
| `list` | `list(*, project=None) -> list[Task]` | list (sorted by label, uri) | — |
| `dependencies` | `dependencies(uri: str) -> list[str]` | dependency URIs | — |

`owner`, `project`, and `depends_on` accept either a URI string or a
`NamedNode`. `set_status` does not itself enforce transitions; use
`TaskCoordinator` for guarded mutations.

### Example

```python
from selma.memory import MemoryAPI, EmbeddedOxigraph
from selma.agents import TaskService

ts = TaskService(MemoryAPI(EmbeddedOxigraph()), stated_by="https://selma.example/ns/core#self")
u = ts.create("write memory ref", due_by="2026-07-10T17:00:00")
ts.set_status(u, "in_progress")
ts.add_dependency(u, "https://selma.example/ns/instance/task/outline")
print(ts.get(u).status)              # "in_progress"
print(ts.dependencies(u))
```

## `TaskCoordinator`

```python
TaskCoordinator(memory, *, stated_by) -> None
```

Coordination layer over `TaskService` that enforces status transitions and
provides project-scoped views. Allowed transitions:
`open → in_progress/blocked`, `in_progress → done/blocked`,
`blocked → in_progress/open`, `done → ∅`.

| Method | Signature | Returns | Raises |
|--------|-----------|---------|--------|
| `open_tasks` | `open_tasks(project: str) -> list[Task]` | open/in_progress tasks, sorted by deadline | — |
| `blocked_tasks` | `blocked_tasks(*, project=None) -> list[Task]` | blocked tasks (sorted by label, uri) | — |
| `blockers` | `blockers(uri: str) -> list[str]` | not-done dependency URIs | — |
| `claim` | `claim(uri: str, *, owner: str) -> None` | — | `TaskNotFoundError`, `InvalidStatusTransitionError` |
| `complete` | `complete(uri: str) -> None` | — | `TaskNotFoundError`, `InvalidStatusTransitionError` |
| `block` | `block(uri: str, *, reason: str) -> None` | — | `TaskNotFoundError`, `InvalidStatusTransitionError` |

`claim` sets status to `in_progress` and `ownedBy` to the claiming agent.
`complete` sets status to `done` and `completedAt` to now. `block` sets
status to `blocked` and records an `agents:blockReason` fact.

### Example

```python
from selma.memory import MemoryAPI, EmbeddedOxigraph
from selma.agents import TaskCoordinator

c = TaskCoordinator(MemoryAPI(EmbeddedOxigraph()), stated_by="https://selma.example/ns/core#self")
# ...create project p and tasks t1, t2 with t2 depends_on t1...
c.claim(t1, owner="https://selma.example/ns/core#self")
c.complete(t1)
print(c.blockers(t2))            # [] once t1 is done
print([t.label for t in c.open_tasks(p)])
```

## `AgentRunner`

```python
AgentRunner(memory: MemoryAPI, *, agent: str = AGENT_SELF, stated_by=None) -> None
```

Runs a single task end-to-end. `run` claims the task, invokes the executor,
records the outcome, and updates the status. v1 is sequential (one task per
`run` call); there is no parallelism and no persistent queue.

| Method | Signature | Returns | Raises |
|--------|-----------|---------|--------|
| `run` | `run(task_uri: str, executor: Callable[[str, MemoryAPI], str]) -> str` | executor's return value | `TaskNotClaimableError`, re-raised executor exception |

On success the task is completed (status → `done`, `completedAt` → now) and
`agents:executionResult` is set to the executor's return value. On exception
the task is blocked (status → `blocked`, `agents:blockReason` ← exception
message) and the exception is re-raised.

### Example

```python
from selma.memory import MemoryAPI, EmbeddedOxigraph
from selma.agents import AgentRunner

runner = AgentRunner(MemoryAPI(EmbeddedOxigraph()), agent="https://selma.example/ns/core#self")

def executor(task_uri, mem):
    # Do the work, return a result string.
    return "done: wrote 12 lines"

result = runner.run("https://selma.example/ns/instance/task/1", executor)
print(result)   # "done: wrote 12 lines"
```

## Dataclasses

### `Project`

```python
@dataclass(frozen=True)
class Project:
    uri: str
    label: str | None = None
    description: str | None = None
    part_of: str | None = None
```

Class method `Project.from_row(row)` builds an instance from a pyoxigraph
`QuerySolution`.

### `Task`

```python
@dataclass(frozen=True)
class Task:
    uri: str
    label: str | None = None
    description: str | None = None
    status: str | None = None
    owned_by: str | None = None
    due_by: str | None = None
    completed_at: str | None = None
    part_of: str | None = None
    block_reason: str | None = None
    execution_result: str | None = None
```

Class method `Task.from_row(row)` builds an instance from a pyoxigraph
`QuerySolution`.

## Exceptions

| Exception | When raised |
|-----------|-------------|
| `AgentsError` | Base class for all `selma.agents` errors (subclass of `MemoryError`). |
| `ProjectNotFoundError` | `ProjectService.get` called with a project URI not in memory. |
| `TaskNotFoundError` | `TaskService.get` or coordinator method called with a task URI not in memory. |
| `InvalidStatusTransitionError` | `claim`/`complete`/`block` requested a transition not in the allowed table. |
| `TaskNotClaimableError` | `AgentRunner.run` called on a task whose status is not `open` or `in_progress`. |

## Cross-references

- Architecture overview: [../architecture.md](../architecture.md)
- Memory API reference: [memory.md](memory.md)
- Life API reference: [life.md](life.md)
- Voice API reference: [voice.md](voice.md)
- Design spec: [../superpowers/specs/2026-07-06-selma-agents-design.md](../superpowers/specs/2026-07-06-selma-agents-design.md)