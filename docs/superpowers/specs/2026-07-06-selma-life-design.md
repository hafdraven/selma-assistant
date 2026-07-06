# Selma Life — Design Spec

**Date:** 2026-07-06
**Status:** Design (pending implementation)
**Sub-project:** `selma.life` — life-assistant core of the Selma assistant platform
**Spec language:** English
**Depends on:** `selma.memory` (typed `MemoryAPI` + core ontology)

---

## 1. Scope & Position in the Platform

This spec covers **`selma.life`** — the life-assistant core of the Selma platform. It is the
second sub-project, a pure client of `selma.memory`. Per the platform vision ("follow all my
life activities, remind, support, schedule my time") and memory core spec §8, `selma.life`
provides reminders, scheduling, and activity capture on top of the typed memory API.

### What this subsystem does

- **Reminders** — create, list, and fire reminders. A reminder is stored in memory as a
  `selma:Reminder` (subclass of `selma:Event`) with a `selma:validFrom` fire time and a link
  (`life:remindsAbout`) to whatever it reminds about. A `ReminderService` checks due reminders
  and triggers caller-supplied callbacks via an in-process scheduler (stdlib only).
- **Scheduling** — manage time blocks on a timeline. Events are stored as `selma:Event` with
  `selma:validFrom`/`selma:validTo` (start/end), a `selma:label`, and optional `selma:partOf`
  links to tasks or projects. A `ScheduleService` provides day/week views, move, cancel, and
  conflict detection.
- **Activity capture** — record what the user is doing. Activities are `selma:Event` instances
  with a start (`selma:validFrom`), optional end (`selma:validTo`), `selma:label`, `selma:tag`
  values, and optional `selma:partOf` links. An `ActivityService` supports start/stop and
  history queries.

### What this subsystem does NOT do (out of scope, other sub-projects)

- HTTP endpoints or external integrations — those are `selma.voice`.
- Autonomous task execution or project coordination — that is `selma.agents`.
- Natural-language understanding — turning user input into `selma.life` calls is the caller's
  job.
- Notifications delivery (push, email, TTS) — `selma.life` fires a callback; the caller
  decides how to surface it.
- Persistence or storage implementation — all state lives in `selma.memory` via `MemoryAPI`.

### Package shape

A Python library (`selma.life`) at `src/selma/life/`, imported alongside `selma.memory`. No
HTTP wrapper. The public surface is three services plus a thin `LifeAssistant` facade.

---

## 2. Life Namespace & Terms

`selma.life` reuses `selma:Reminder`, `selma:Event`, `selma:Task`, `selma:Project`, and core
properties. Two life-specific properties are minted in a separate namespace:

Namespace: `https://selma.example/ns/life#` (prefix `life:`).

| Property | Domain → Range | Purpose |
|----------|----------------|---------|
| `life:remindsAbout` | `selma:Reminder` → `selma:Entity` | Links a reminder to its target. |
| `life:firedAt` | `selma:Reminder` → `xsd:dateTime` | Set when a reminder has fired; null until then. |

Instance URIs: `life:reminder/<id>`, `life:event/<id>`, `life:activity/<id>`.

---

## 3. Storage & Data Model

All state is stored in `selma.memory` through `MemoryAPI`. Two storage calls per entity:

1. **Type assertion** — `api.ask("INSERT DATA { GRAPH <selma:default> { <uri> a selma:Reminder } }")`
   — puts `rdf:type` in a named graph so `find(class_uri)` discovers it.
2. **Property facts** — `api.remember(uri, predicate, obj, stated_by=...)` — reified facts in
   the default graph, queryable via `recall` with `as_of` time-travel.

### Entity shapes

**Reminder** (`selma:Reminder`): `rdf:type`, `selma:validFrom` (fire time), `selma:label`,
`life:remindsAbout`, `life:firedAt` (set on fire).

**Scheduled event** (`selma:Event`): `rdf:type`, `selma:validFrom` (start), `selma:validTo`
(end), `selma:label`, `selma:partOf`.

**Activity** (`selma:Event`): `rdf:type`, `selma:validFrom` (start), `selma:validTo` (set on
stop), `selma:label`, `selma:tag` (one per tag), `selma:partOf`.

Activities and scheduled events are both `selma:Event`, distinguished by query (unbounded
`validTo` = running activity).

---

## 4. Public API Surface

### ReminderService

```python
class ReminderService:
    def __init__(self, memory: MemoryAPI, *, stated_by) -> None: ...
    def create(self, fire_at: str, *, about=None, label=None) -> str: ...
    def fire(self, uri: str, *, now: str | None = None) -> None: ...
    def list(self, *, due_before=None, include_fired=False) -> list[Reminder]: ...
    def get(self, uri: str) -> Reminder: ...
    def check_due(self, *, now: str | None = None) -> list[str]: ...
    def start(self, callback, *, interval: float = 30.0) -> None: ...
    def stop(self) -> None: ...
```

### ScheduleService

```python
class ScheduleService:
    def __init__(self, memory: MemoryAPI, *, stated_by) -> None: ...
    def create(self, start: str, end: str, *, label=None, part_of=None) -> str: ...
    def list(self, *, day=None, week=None) -> list[ScheduleEvent]: ...
    def get(self, uri: str) -> ScheduleEvent: ...
    def move(self, uri: str, new_start: str, *, new_end=None) -> None: ...
    def cancel(self, uri: str) -> None: ...
    def conflicts(self, start: str, end: str, *, exclude=None) -> list[str]: ...
```

### ActivityService

```python
class ActivityService:
    def __init__(self, memory: MemoryAPI, *, stated_by) -> None: ...
    def start(self, label: str, *, tags=(), part_of=None, at=None) -> str: ...
    def stop(self, uri: str, *, at=None) -> None: ...
    def current(self) -> Activity | None: ...
    def history(self, *, since=None, until=None, tags=()) -> list[Activity]: ...
```

### LifeAssistant facade

```python
class LifeAssistant:
    def __init__(self, memory: MemoryAPI, *, stated_by=None) -> None: ...
    @property
    def reminders(self) -> ReminderService: ...
    @property
    def schedule(self) -> ScheduleService: ...
    @property
    def activities(self) -> ActivityService: ...
    def describe(self) -> dict: ...
```

---

## 5. Module Structure

```
src/selma/life/
├── __init__.py      # Public exports
├── terms.py         # life: namespace, PROPS, instance URI minting
├── models.py        # Reminder, ScheduleEvent, Activity dataclasses
├── reminders.py     # ReminderService + threading.Timer loop
├── schedule.py      # ScheduleService
├── activity.py      # ActivityService
├── assistant.py     # LifeAssistant facade
└── exceptions.py    # LifeError hierarchy
```

---

## 6. Reminder Firing Mechanism

In-process polling loop using `threading.Timer`. `check_due(now=...)` is a synchronous,
testable function over memory: it finds unfired reminders with `validFrom <= now`, sets
`life:firedAt`, and returns fired URIs. `start(callback, interval=30.0)` runs a background
loop calling `check_due` and dispatching to `callback(reminder_uri)`. Idempotent via
`FILTER NOT EXISTS { ?r life:firedAt ?f }`.

---

## 7. Error Handling

Reuses `selma.memory.exceptions` for store-level failures. Life-specific hierarchy:

- `LifeError(MemoryError)` — base
  - `ScheduleConflictError` — create/move overlap
  - `ReminderNotDueError` — fire on future reminder
  - `ReminderNotFoundError` — unknown URI
  - `ReminderSchedulerError` — start while running
  - `ActivityNotRunningError` — stop on already-stopped
  - `ActivityAlreadyRunningError` — start while running

---

## 8. Decisions Log

| Decision | Choice | Alternatives |
|----------|--------|-------------|
| Position | Pure client of MemoryAPI | Own DB; extend memory core |
| Life terms | Two properties in `life:` namespace | Extend core ontology; full life ontology |
| Type assertion | `ask` INSERT into named graph | `remember` the type (invisible to `find`) |
| Reminder firing | Polling `threading.Timer` loop | `sched.scheduler`; one Timer per reminder |
| Move/reschedule | `forget(soft=True)` + fresh `remember` | `supersede` (ambiguous for multi-fact) |
| Activities vs events | Both `selma:Event`; distinguished by query | A `life:Activity` subclass |
| Single running activity | v1 enforces one | Multiple concurrent (deferred) |
| Notification delivery | Out of scope; callback only | Built-in push/TTS (belongs in `selma.voice`) |