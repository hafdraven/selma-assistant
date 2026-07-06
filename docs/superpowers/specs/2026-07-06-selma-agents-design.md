# Selma Agents — Design Spec

**Date:** 2026-07-06
**Status:** Design (pending implementation)
**Sub-project:** `selma.agents` — autonomous task execution and project coordination
**Spec language:** English
**Depends on:** `selma.memory` (typed `MemoryAPI` + core ontology)

---

## 1. Scope & Position in the Platform

This spec covers **`selma.agents`** — the autonomous task execution and project
coordination sub-project of the Selma platform. It is the third sub-project, a
pure client of `selma.memory`. Per the platform vision ("follow my projects and
coordinate autonomous execution of tasks") and memory core spec §8,
`selma.agents` provides project management, task management, task coordination,
and autonomous task execution on top of the typed memory API.

### What this subsystem does

- **Project management** — create, list, get projects. A project is a
  `selma:Project` with a `selma:label`, `selma:description`, and optional
  `selma:partOf` link (sub-projects).
- **Task management** — create, list, get tasks within projects. A task is a
  `selma:Task` with `selma:hasStatus` (open / in_progress / done / blocked),
  `selma:ownedBy` (Agent URI), optional `selma:dueBy`, `selma:completedAt`, and
  `selma:partOf` (parent Project). Status changes are stored as superseded
  facts so history is preserved.
- **Task coordination** — a `TaskCoordinator` lists open tasks for a project
  (sorted by deadline), claims a task (in_progress + ownedBy), completes a task
  (done + completedAt), blocks a task (blocked + reason), lists blocked tasks
  and their blockers, and queries `selma:dependsOn` dependencies.
- **Autonomous execution** — an `AgentRunner` takes a task and an executor
  callable, claims the task, runs the executor, records the outcome
  (success/failure) in memory, and updates the task status. v1 is sequential
  (one task at a time per runner); no parallelism.

### What this subsystem does NOT do (out of scope)

- Parallel/concurrent task execution — v1 is sequential per runner.
- Scheduling *when* tasks run — that is the caller's responsibility.
- HTTP endpoints or external integrations — those belong to other sub-projects.
- Natural-language understanding — turning user input into `selma.agents` calls
  is the caller's job.
- Persistence or storage implementation — all state lives in `selma.memory`.

### Package shape

A Python library (`selma.agents`) at `src/selma/agents/`, imported alongside
`selma.memory` and `selma.life`. No HTTP wrapper. The public surface is four
services plus a thin `AgentsAssistant` facade.

---

## 2. Agents Namespace & Terms

`selma.agents` reuses `selma:Task`, `selma:Project`, `selma:Agent`, and core
properties (`hasStatus`, `ownedBy`, `dueBy`, `completedAt`, `partOf`,
`dependsOn`, `label`, `description`). Two agents-specific properties are minted
in a separate namespace:

Namespace: `https://selma.example/ns/agents#` (prefix `agents:`).

| Property | Domain → Range | Purpose |
|----------|----------------|---------|
| `agents:executionResult` | `selma:Task` → `xsd:string` | Result summary an `AgentRunner` stores after running an executor. |
| `agents:blockReason` | `selma:Task` → `xsd:string` | Reason a task was blocked. |

Instance URIs: `agents:project/<id>`, `agents:task/<id>`.

---

## 3. Storage & Data Model

All state is stored in `selma.memory` through `MemoryAPI`. Two storage calls
per entity (same pattern as `selma.life`):

1. **Type assertion** —
   `api.ask("INSERT DATA { GRAPH <selma:default> { <uri> a selma:Task } }")` —
   puts `rdf:type` in a named graph so `find(class_uri)` discovers it.
2. **Property facts** — `api.remember(uri, predicate, obj, stated_by=...)` —
   reified facts in the default graph, queryable via `recall` with `as_of`
   time-travel.

### Entity shapes

**Project** (`selma:Project`): `rdf:type`, `selma:label`, `selma:description`,
optional `selma:partOf` (parent project).

**Task** (`selma:Task`): `rdf:type`, `selma:label`, `selma:description`,
`selma:hasStatus` (one of open/in_progress/done/blocked), `selma:ownedBy`
(Agent URI), optional `selma:dueBy` (xsd:dateTime), `selma:completedAt`
(xsd:dateTime, set on completion), `selma:partOf` (parent Project),
`selma:dependsOn` (another Task), `agents:executionResult`,
`agents:blockReason`.

### Status transitions

Status and owner changes retire the old fact (soft ``forget``: the old
reification node gets ``validTo = now``) and assert a fresh replacement via
``remember``, preserving history. This follows the same pattern as
`selma.life`'s `ScheduleService.move` rather than `supersede`, because
`supersede` is ambiguous for multi-fact subjects: it picks the first fact's
predicate regardless of which predicate you intend to retire, and refuses once
any fact about the subject already has a `validTo`. Allowed transitions:

- open → in_progress (claim)
- in_progress → done (complete)
- in_progress → blocked (block)
- open → blocked (block)

`ownedBy` changes follow the same soft-forget + remember pattern.

---

## 4. Public API Surface

### ProjectService

```python
class ProjectService:
    def __init__(self, memory: MemoryAPI, *, stated_by) -> None: ...
    def create(self, label: str, *, description=None, part_of=None) -> str: ...
    def get(self, uri: str) -> Project: ...
    def list(self) -> list[Project]: ...
```

### TaskService

```python
class TaskService:
    def __init__(self, memory: MemoryAPI, *, stated_by) -> None: ...
    def create(self, label: str, *, project=None, description=None,
               owner=None, due_by=None, depends_on=None) -> str: ...
    def get(self, uri: str) -> Task: ...
    def list(self, *, project=None) -> list[Task]: ...
    def set_status(self, uri: str, status: str) -> None: ...
    def set_owner(self, uri: str, owner: str) -> None: ...
    def add_dependency(self, uri: str, depends_on: str) -> None: ...
    def dependencies(self, uri: str) -> list[str]: ...
```

### TaskCoordinator

```python
class TaskCoordinator:
    def __init__(self, memory: MemoryAPI, *, stated_by) -> None: ...
    def open_tasks(self, project: str) -> list[Task]: ...
    def claim(self, uri: str, *, owner: str) -> None: ...
    def complete(self, uri: str) -> None: ...
    def block(self, uri: str, *, reason: str) -> None: ...
    def blocked_tasks(self, *, project=None) -> list[Task]: ...
    def blockers(self, uri: str) -> list[str]: ...
```

### AgentRunner

```python
class AgentRunner:
    def __init__(self, memory: MemoryAPI, *, agent: str, stated_by) -> None: ...
    def run(self, task_uri: str, executor: Callable[[str, MemoryAPI], str]) -> str: ...
```

`executor(task_uri: str, memory: MemoryAPI) -> str` returns a result summary.
The runner claims the task (status → in_progress, ownedBy → agent), runs the
executor, stores the result via `agents:executionResult`, and either completes
the task (status → done, completedAt → now) or blocks it (status → blocked,
`agents:blockReason` ← exception message) based on whether the executor
raises. Returns the executor's result summary on success.

### AgentsAssistant facade

```python
class AgentsAssistant:
    def __init__(self, memory: MemoryAPI, *, stated_by=None) -> None: ...
    @property
    def projects(self) -> ProjectService: ...
    @property
    def tasks(self) -> TaskService: ...
    @property
    def coordinator(self) -> TaskCoordinator: ...
    @property
    def runner(self) -> AgentRunner: ...
    def describe(self) -> dict: ...
```

---

## 5. Module Structure

```
src/selma/agents/
├── __init__.py      # Public exports
├── terms.py         # agents: namespace, PROPS, instance URI minting
├── models.py        # Project, Task dataclasses
├── exceptions.py    # AgentsError hierarchy
├── queries.py       # SPARQL query builders
├── projects.py      # ProjectService
├── tasks.py         # TaskService
├── coordinator.py   # TaskCoordinator
├── runner.py        # AgentRunner
└── assistant.py     # AgentsAssistant facade
```

---

## 6. Autonomous Execution Mechanism

`AgentRunner.run(task_uri, executor)` is synchronous and sequential. It:

1. Loads the task and validates it is in a claimable state (open or
   in_progress).
2. Claims the task: `supersede` `hasStatus` → `in_progress`, `supersede`
   `ownedBy` → agent URI.
3. Calls `executor(task_uri, memory)`. The executor may itself use memory.
4. On success: stores `agents:executionResult` ← result summary,
   `supersede` `hasStatus` → `done`, sets `completedAt` ← now. Returns the
   result summary.
5. On exception: stores `agents:blockReason` ← exception message,
   `supersede` `hasStatus` → `blocked`. Re-raises.

A runner is single-use per `run` call; there is no persistent queue in v1. The
caller decides which tasks to run and in what order.

---

## 7. Error Handling

Reuses `selma.memory.exceptions` for store-level failures. Agents-specific
hierarchy:

- `AgentsError(MemoryError)` — base
  - `ProjectNotFoundError` — unknown project URI
  - `TaskNotFoundError` — unknown task URI
  - `InvalidStatusTransitionError` — disallowed status transition
  - `TaskNotClaimableError` — claim on a task not in an open/in_progress state

---

## 8. Decisions Log

| Decision | Choice | Alternatives |
|----------|--------|-------------|
| Position | Pure client of MemoryAPI | Own DB; extend memory core |
| Agents terms | Two properties in `agents:` namespace | Extend core ontology |
| Type assertion | `ask` INSERT into named graph | `remember` the type (invisible to `find`) |
| Status changes | `forget(soft=True)` + `remember` (preserves history) | `supersede` (ambiguous for multi-fact subjects) |
| Execution model | Synchronous, sequential, single runner | Parallel; persistent queue |
| Block reason | `agents:blockReason` literal | `selma:source` on the status fact |
| Dependencies | `selma:dependsOn` (core, transitive) | New `agents:dependsOn` |