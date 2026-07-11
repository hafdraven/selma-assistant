# Tutorial 1: Reminders and Scheduling

This tutorial walks through the `selma.life` sub-project end to end: setting up
the life assistant, creating and firing reminders, starting the background
scheduler, scheduling events with conflict detection, and tracking activities.
By the end you will have a single runnable script that exercises every service.

> **Prerequisites**: Install Selma with `pip install -e ".[dev]"`. See the
> [getting-started guide](../getting-started.md) if you have not done this yet.

## What you will build

A script that:

1. Creates a `LifeAssistant` over an in-memory store.
2. Creates a reminder, fires it, and polls with `check_due`.
3. Starts the reminder scheduler with a callback.
4. Schedules two events, detects a conflict, and moves an event.
5. Tracks an activity through start → stop → history.

## Step 1 — Set up the LifeAssistant

`LifeAssistant` is a thin facade over three services: `ReminderService`,
`ScheduleService`, and `ActivityService`. All three share the same `MemoryAPI`
instance and the same `stated_by` provenance agent, so every fact they store
is traceable to the same source.

```python
from selma.memory import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph
from selma.life import LifeAssistant

memory = MemoryAPI(EmbeddedOxigraph())
life = LifeAssistant(memory)
```

`EmbeddedOxigraph()` with no arguments keeps the store in RAM. Pass
`path="~/.selma/memory"` to persist to disk instead.

## Step 2 — Create a reminder

Reminders are `selma:Reminder` instances with a `validFrom` (fire time) and an
optional `label`. The `create` method returns the reminder's URI.

```python
reminder_uri = life.reminders.create(
    "2026-07-06T09:00:00",
    label="Team standup",
)
print("reminder:", reminder_uri)
```

List all reminders to see what is stored:

```python
for r in life.reminders.list():
    print(f"  {r.label} at {r.fire_at} (fired: {r.fired_at})")
```

Output:

```
  Team standup at 2026-07-06T09:00:00 (fired: None)
```

## Step 3 — Fire due reminders with check_due

`check_due` is the idempotent poll: it finds all unfired reminders whose fire
time has passed, marks them as fired by setting `life:firedAt`, and returns
their URIs. Calling it again returns an empty list because the reminders are
already marked.

```python
# Simulate time having passed: fire_at is in the past relative to "now".
# In this example, pass an explicit `now` that is after the fire time.
due = life.reminders.check_due(now="2026-07-06T09:30:00")
print("due:", due)
# ['https://selma.example/ns/life#reminder/...']

due_again = life.reminders.check_due(now="2026-07-06T09:31:00")
print("due again:", due_again)
# []
```

You can also fire a single reminder explicitly with `fire(uri)`. It raises
`ReminderNotDueError` if the fire time has not arrived yet, and is a no-op if
the reminder was already fired.

## Step 4 — Start the scheduler with a callback

The scheduler is a daemon `threading.Timer` poll loop. `start(callback,
interval=)` launches it; every `interval` seconds it calls `check_due` and
dispatches each due URI to your callback. `stop()` cancels the timer.

```python
def on_fire(uri):
    print(f"  [scheduler] fired: {uri}")

life.reminders.start(on_fire, interval=1.0)

# Create a reminder that fires in ~2 seconds.  In a real app you would
# use a real future timestamp; here we use a past time so check_due
# picks it up immediately on the first poll.
short = life.reminders.create("2025-01-01T00:00:00", label="quick test")

import time
time.sleep(1.5)  # let the scheduler poll once

life.reminders.stop()
```

The scheduler is idempotent: the `FILTER NOT EXISTS { ?r life:firedAt ?f }`
guard in the `check_due` query prevents double-firing even if the poll runs
concurrently.

## Step 5 — Schedule an event

Scheduled events are `selma:Event` instances with a `validFrom` (start) and
`validTo` (end). The `create` method checks for conflicts first and raises
`ScheduleConflictError` if the new event overlaps an existing one.

```python
event1 = life.schedule.create(
    "2026-07-06T09:00:00", "2026-07-06T10:00:00",
    label="Standup meeting",
)
print("event1:", event1)

event2 = life.schedule.create(
    "2026-07-06T11:00:00", "2026-07-06T12:00:00",
    label="Design review",
)
print("event2:", event2)
```

List events for a specific day:

```python
for ev in life.schedule.list(day="2026-07-06"):
    print(f"  {ev.label}: {ev.start}–{ev.end}")
```

Output:

```
  Standup meeting: 2026-07-06T09:00:00–2026-07-06T10:00:00
  Design review: 2026-07-06T11:00:00–2026-07-06T12:00:00
```

## Step 6 — Detect a conflict

`conflicts(start, end, *, exclude=None)` returns the URIs of events that
overlap the given time range. `create` calls this internally, but you can use
it directly to check before scheduling.

```python
from selma.life import ScheduleConflictError

try:
    life.schedule.create(
        "2026-07-06T09:30:00", "2026-07-06T10:30:00",
        label="Overlapping meeting",
    )
except ScheduleConflictError as e:
    print("conflict:", e)
# conflict: event 2026-07-06T09:30:00..2026-07-06T10:30:00 overlaps an existing event
```

You can also call `conflicts` directly to see which events overlap:

```python
print("overlaps:", life.schedule.conflicts("2026-07-06T09:30:00",
                                             "2026-07-06T10:30:00"))
# ['https://selma.example/ns/life#event/...']
```

## Step 7 — Move an event

`move(uri, new_start, *, new_end=None)` retires the old start/end facts
(soft-delete) and asserts fresh ones, preserving history. When `new_end` is
omitted, the event duration is preserved. `move` also checks for conflicts
(excluding the event being moved) and raises `ScheduleConflictError` on
overlap.

```python
life.schedule.move(event1, "2026-07-06T14:00:00")
moved = life.schedule.get(event1)
print(f"moved: {moved.label} {moved.start}–{moved.end}")
# moved: Standup meeting 2026-07-06T14:00:00–2026-07-06T15:00:00
```

The old 9:00–10:00 facts are still in memory with a `validTo` set, so the full
history of the event's position on the timeline is retained. `recall` with
`include_history=True` would show both the old and new start/end values.

## Step 8 — Track an activity

Activities are `selma:Event` instances with a start (`validFrom`), optional
end (`validTo`, set on stop), `label`, and `tag` values. v1 enforces a single
running activity: calling `start` while another activity is running raises
`ActivityAlreadyRunningError`.

```python
activity_uri = life.activities.start(
    "writing docs",
    tags=("selma", "docs"),
)
print("activity:", activity_uri)

current = life.activities.current()
print("current:", current.label, current.tags)
# current: writing docs ['docs', 'selma']

life.activities.stop(activity_uri)
print("current after stop:", life.activities.current())
# current after stop: None
```

View the activity history, optionally filtered by tag:

```python
for a in life.activities.history(tags=("docs",)):
    print(f"  {a.label} ({a.tags}) {a.start}–{a.end}")
#   writing docs (['docs', 'selma']) 2026-07-06T...–2026-07-06T...
```

## Complete runnable script

The following script ties all the steps together. Save it as
`life_tutorial.py` and run it with `python life_tutorial.py`.

```python
"""Tutorial 1: reminders, scheduling, and activity tracking."""
from __future__ import annotations

import time

from selma.memory import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph
from selma.life import LifeAssistant, ScheduleConflictError


def main() -> None:
    # 1. Set up the LifeAssistant over an in-memory store.
    memory = MemoryAPI(EmbeddedOxigraph())
    life = LifeAssistant(memory)
    print("=== LifeAssistant ready ===")
    print(life.describe())

    # 2. Create a reminder.
    reminder_uri = life.reminders.create(
        "2026-07-06T09:00:00",
        label="Team standup",
    )
    print("\n=== Reminder created ===")
    print("  uri:", reminder_uri)
    for r in life.reminders.list():
        print(f"  {r.label} at {r.fire_at} (fired: {r.fired_at})")

    # 3. Fire due reminders with check_due (idempotent).
    print("\n=== check_due ===")
    due = life.reminders.check_due(now="2026-07-06T09:30:00")
    print("  due:", due)
    due_again = life.reminders.check_due(now="2026-07-06T09:31:00")
    print("  due again (idempotent):", due_again)

    # 4. Start the scheduler with a callback.
    print("\n=== Scheduler ===")
    def on_fire(uri: str) -> None:
        print(f"  [scheduler] fired: {uri}")

    life.reminders.start(on_fire, interval=1.0)
    life.reminders.create("2025-01-01T00:00:00", label="quick test")
    time.sleep(1.5)
    life.reminders.stop()
    print("  scheduler stopped")

    # 5. Schedule two events.
    print("\n=== Schedule ===")
    event1 = life.schedule.create(
        "2026-07-06T09:00:00", "2026-07-06T10:00:00",
        label="Standup meeting",
    )
    event2 = life.schedule.create(
        "2026-07-06T11:00:00", "2026-07-06T12:00:00",
        label="Design review",
    )
    print("  event1:", event1)
    print("  event2:", event2)
    for ev in life.schedule.list(day="2026-07-06"):
        print(f"    {ev.label}: {ev.start}–{ev.end}")

    # 6. Detect a conflict.
    print("\n=== Conflict detection ===")
    try:
        life.schedule.create(
            "2026-07-06T09:30:00", "2026-07-06T10:30:00",
            label="Overlapping meeting",
        )
    except ScheduleConflictError as e:
        print("  caught:", e)
    print("  overlaps:", life.schedule.conflicts(
        "2026-07-06T09:30:00", "2026-07-06T10:30:00"))

    # 7. Move an event (preserves duration, retains history).
    print("\n=== Move event ===")
    life.schedule.move(event1, "2026-07-06T14:00:00")
    moved = life.schedule.get(event1)
    print(f"  moved: {moved.label} {moved.start}–{moved.end}")

    # 8. Track an activity.
    print("\n=== Activity tracking ===")
    activity_uri = life.activities.start(
        "writing docs",
        tags=("selma", "docs"),
    )
    print("  activity:", activity_uri)
    current = life.activities.current()
    print("  current:", current.label, current.tags)

    life.activities.stop(activity_uri)
    print("  current after stop:", life.activities.current())

    print("\n=== Activity history (tag=docs) ===")
    for a in life.activities.history(tags=("docs",)):
        print(f"  {a.label} ({a.tags}) {a.start}–{a.end}")

    print("\nDone.")


if __name__ == "__main__":
    main()
```

## Next steps

- [Tutorial 2: Custom Voice Intent](02-custom-voice-intent.md) — register a
  custom intent handler on the voice gateway.
- [Tutorial 3: Custom Agent](03-custom-agent.md) — write an executor and run a
  task autonomously.
- [Life API reference](../api-reference/life.md) — full method signatures and
  dataclass fields.