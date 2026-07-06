# `selma.life` API reference

`selma.life` is the life-assistant core: reminders, scheduling, and activity
tracking. It is a pure client of `selma.memory` — every entity is stored as a
reified fact through `MemoryAPI`. The public surface is three services plus a
thin `LifeAssistant` facade and three plain dataclasses.

## Public exports

| Name | Kind | Description |
|------|------|-------------|
| `LifeAssistant` | class | Facade over the three life services. |
| `ReminderService` | class | Create, list, fire, and poll reminders. |
| `ScheduleService` | class | Time blocks on a timeline with conflict detection. |
| `ActivityService` | class | Capture what the user is doing (single running activity). |
| `Reminder` | dataclass | A `selma:Reminder` with fire time, optional label and target. |
| `ScheduleEvent` | dataclass | A scheduled `selma:Event` with start, end, optional label and parent. |
| `Activity` | dataclass | An activity `selma:Event` with start, optional end, label, tags. |
| `LifeError` | exception | Base class for all `selma.life` errors. |
| `ScheduleConflictError` | exception | A create/move would overlap an existing event. |
| `ReminderNotDueError` | exception | `fire` called before the reminder's fire time. |
| `ReminderNotFoundError` | exception | A reminder URI was not found in memory. |
| `ReminderSchedulerError` | exception | The scheduler was started while already running. |
| `ActivityNotRunningError` | exception | `stop` called on an activity that is not running. |
| `ActivityAlreadyRunningError` | exception | `start` called while another activity is already running. |

## `LifeAssistant`

```python
LifeAssistant(memory, *, stated_by=None) -> None
```

Thin facade over `ReminderService`, `ScheduleService`, and `ActivityService`,
all sharing the same `memory` (`MemoryAPI`) and `stated_by` provenance agent.
`stated_by` defaults to the platform default agent.

| Member | Signature | Returns |
|--------|-----------|---------|
| `reminders` | property | `ReminderService` |
| `schedule` | property | `ScheduleService` |
| `activities` | property | `ActivityService` |
| `describe` | `describe() -> dict` | compact surface description |

### Example

```python
from selma.memory import MemoryAPI, EmbeddedOxigraph
from selma.life import LifeAssistant

life = LifeAssistant(MemoryAPI(EmbeddedOxigraph()))
r = life.reminders.create("2026-07-06T15:00:00", label="call mom")
print(life.reminders.list())
e = life.schedule.create("2026-07-06T09:00:00", "2026-07-06T10:00:00",
                         label="standup")
print(life.schedule.list(day="2026-07-06"))
```

## `ReminderService`

```python
ReminderService(memory, *, stated_by) -> None
```

Reminders are `selma:Reminder` instances: a type assertion in the
`selma:default` named graph plus reified property facts. Firing sets
`life:firedAt`; `check_due` is idempotent via a `FILTER NOT EXISTS` guard.

| Method | Signature | Returns | Raises |
|--------|-----------|---------|--------|
| `create` | `create(fire_at: str, *, about=None, label=None) -> str` | reminder URI | — |
| `get` | `get(uri: str) -> Reminder` | `Reminder` | `ReminderNotFoundError` |
| `list` | `list(*, due_before=None, include_fired=False) -> list[Reminder]` | list | — |
| `fire` | `fire(uri: str, *, now: str \| None = None) -> None` | — | `ReminderNotFoundError`, `ReminderNotDueError` |
| `check_due` | `check_due(*, now: str \| None = None) -> list[str]` | due URIs | — |
| `start` | `start(callback, *, interval: float = 30.0) -> None` | — | `ReminderSchedulerError` |
| `stop` | `stop() -> None` | — | — |

`fire` is idempotent: calling it on an already-fired reminder is a no-op.
`start` launches a daemon `threading.Timer` poll loop that calls
`check_due`, dispatches each due URI to `callback`, and re-arms itself.

### Example

```python
from selma.memory import MemoryAPI, EmbeddedOxigraph
from selma.life import ReminderService

rs = ReminderService(MemoryAPI(EmbeddedOxigraph()), stated_by="https://selma.example/ns/core#self")
u = rs.create("2026-07-06T15:00:00", label="call mom")
rs.fire(u)
print(rs.check_due())            # [] — already fired
rs.start(lambda uri: print(uri)) # poll every 30s
rs.stop()
```

## `ScheduleService`

```python
ScheduleService(memory, *, stated_by) -> None
```

Scheduled events are `selma:Event` instances with `validFrom` (start),
`validTo` (end), optional `label` and `partOf`. `move`/`cancel` use
`forget(soft=True)` + a fresh `remember` so history is preserved.

| Method | Signature | Returns | Raises |
|--------|-----------|---------|--------|
| `create` | `create(start: str, end: str, *, label=None, part_of=None) -> str` | event URI | `ScheduleConflictError` |
| `move` | `move(uri: str, new_start: str, *, new_end=None) -> None` | — | `ScheduleConflictError`, `LifeError` |
| `cancel` | `cancel(uri: str) -> None` | — | — |
| `get` | `get(uri: str) -> ScheduleEvent` | `ScheduleEvent` | `LifeError` |
| `list` | `list(*, day=None, week=None) -> list[ScheduleEvent]` | list (sorted by start) | `ValueError` |
| `conflicts` | `conflicts(start: str, end: str, *, exclude=None) -> list[str]` | conflicting URIs | — |

`list` requires exactly one of `day` or `week`. `move` preserves the event
duration when `new_end` is omitted.

### Example

```python
from selma.memory import MemoryAPI, EmbeddedOxigraph
from selma.life import ScheduleService

sc = ScheduleService(MemoryAPI(EmbeddedOxigraph()), stated_by="https://selma.example/ns/core#self")
e = sc.create("2026-07-06T09:00:00", "2026-07-06T10:00:00", label="standup")
sc.move(e, "2026-07-06T11:00:00")     # keeps 1h duration
print(sc.conflicts("2026-07-06T09:30:00", "2026-07-06T11:30:00"))
print([ev.label for ev in sc.list(day="2026-07-06")])
```

## `ActivityService`

```python
ActivityService(memory, *, stated_by) -> None
```

Activities are `selma:Event` instances with a start (`validFrom`), optional
end (`validTo`, set on stop), `label`, `tag` values, and optional `partOf`.
Unbounded `validTo` means running; bounded means completed. v1 enforces a
single running activity.

| Method | Signature | Returns | Raises |
|--------|-----------|---------|--------|
| `start` | `start(label: str, *, tags=(), part_of=None, at=None) -> str` | activity URI | `ActivityAlreadyRunningError` |
| `stop` | `stop(uri: str, *, at=None) -> None` | — | `ActivityNotRunningError` |
| `current` | `current() -> Activity \| None` | running activity or `None` | — |
| `history` | `history(*, since=None, until=None, tags=()) -> list[Activity]` | list (sorted by start) | — |

### Example

```python
from selma.memory import MemoryAPI, EmbeddedOxigraph
from selma.life import ActivityService

a = ActivityService(MemoryAPI(EmbeddedOxigraph()), stated_by="https://selma.example/ns/core#self")
u = a.start("writing docs", tags=("docs", "selma"))
print(a.current())          # Activity(uri=u, start=..., label="writing docs", tags=["docs"])
a.stop(u)
print(a.history(tags=("docs",)))
```

## Dataclasses

### `Reminder`

```python
@dataclass
class Reminder:
    uri: str
    fire_at: str
    label: str | None = None
    about: str | None = None
    fired_at: str | None = None
```

Class method `Reminder.from_row(row)` builds an instance from a pyoxigraph
`QuerySolution`.

### `ScheduleEvent`

```python
@dataclass
class ScheduleEvent:
    uri: str
    start: str
    end: str | None = None
    label: str | None = None
    part_of: str | None = None
```

Class method `ScheduleEvent.from_row(row)` builds an instance from a
pyoxigraph `QuerySolution`.

### `Activity`

```python
@dataclass
class Activity:
    uri: str
    start: str
    end: str | None = None
    label: str | None = None
    tags: list[str] = field(default_factory=list)
    part_of: str | None = None
```

Class method `Activity.from_row(row)` builds an instance from a pyoxigraph
`QuerySolution`.

## Exceptions

| Exception | When raised |
|-----------|-------------|
| `LifeError` | Base class for all `selma.life` errors (subclass of `MemoryError`). |
| `ScheduleConflictError` | `create`/`move` would overlap an existing scheduled event; also `ScheduleService.get` on a missing event (via `LifeError`). |
| `ReminderNotDueError` | `fire` called on a reminder whose `fire_at` is still in the future. |
| `ReminderNotFoundError` | `fire`/`get` called with a reminder URI not in memory. |
| `ReminderSchedulerError` | `start` called while the scheduler is already running. |
| `ActivityNotRunningError` | `stop` called on an activity that is not running. |
| `ActivityAlreadyRunningError` | `start` called while another activity is already running. |

## Cross-references

- Architecture overview: [../architecture.md](../architecture.md)
- Memory API reference: [memory.md](memory.md)
- Agents API reference: [agents.md](agents.md)
- Voice API reference: [voice.md](voice.md)
- Design spec: [../superpowers/specs/2026-07-06-selma-life-design.md](../superpowers/specs/2026-07-06-selma-life-design.md)