# Getting Started with Selma

This guide takes you from a fresh clone to running code in under ten minutes.
You will store a memory fact, create a reminder with the life assistant, send
a voice command through the gateway, and run the test suite.

## Prerequisites

- **Python 3.11 or newer** (developed on 3.14)
- **pip** (bundled with Python 3.11+)
- **git**

Selma has a single runtime dependency, [pyoxigraph](https://pyoxigraph.readthedocs.io/),
which ships pre-built wheels for Windows, macOS, and Linux, so no system-level
RDF store is required.

## Installation

```bash
git clone https://github.com/hafdraven/selma-assistant.git
cd selma-assistant
pip install -e ".[dev]"
```

Verify the import:

```bash
python -c "from selma.memory import MemoryAPI; print('Selma ready')"
```

You should see `Selma ready`. The `.[dev]` extra also installs `pytest` and
`hypothesis` for the test suite.

## Your first memory

The memory core is an RDF/SPARQL store with a typed API on top. Every fact you
store is a reified triple — the (subject, predicate, object) triple plus
provenance metadata (who stated it, when, with what confidence) — so you can
query both *what* is known and *how it came to be known*.

```python
from selma.memory import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph
from pyoxigraph import NamedNode, Literal

memory = MemoryAPI(EmbeddedOxigraph())
memory.remember(
    NamedNode("http://example/meeting"),
    NamedNode("http://example/topic"),
    Literal("budget review"),
    stated_by=NamedNode("https://selma.example/ns/core#self"),
)
rows = memory.recall(subject=NamedNode("http://example/meeting"))
for row in rows:
    print(f"{row['p'].value}: {row['o'].value}")
```

Output:

```
http://example/topic: budget review
```

`EmbeddedOxigraph()` with no arguments keeps the store in RAM; pass `path=`
to persist to disk, for example `EmbeddedOxigraph(path="~/.selma/memory")`.

## Your first life assistant

The life assistant wraps the memory core with three services: reminders,
scheduling, and activity tracking. All three store their data as reified facts
through `MemoryAPI`, so everything you create is queryable via SPARQL as well.

```python
from selma.memory import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph
from selma.life import LifeAssistant
from pyoxigraph import NamedNode

memory = MemoryAPI(EmbeddedOxigraph())
life = LifeAssistant(memory, stated_by=NamedNode("https://selma.example/ns/core#self"))

# Create a reminder for 9am on July 6th.
reminder_uri = life.reminders.create("2026-07-06T09:00:00", label="Team standup")
print("reminder:", reminder_uri)

# List all reminders.
for r in life.reminders.list():
    print(f"  {r.label} at {r.fire_at} (fired: {r.fired_at})")

# Start an activity, then stop it.
activity_uri = life.activities.start("writing docs", tags=("selma", "docs"))
print("activity:", activity_uri)
print("current:", life.activities.current().label)
life.activities.stop(activity_uri)
print("current after stop:", life.activities.current())
```

Output:

```
reminder: https://selma.example/ns/life#reminder/...
  Team standup at 2026-07-06T09:00:00 (fired: None)
activity: https://selma.example/ns/life#activity/...
current: writing docs
current after stop: None
```

The reminder scheduler is an opt-in polling loop built on
`threading.Timer`. Start it with a callback and an interval (seconds):

```python
life.reminders.start(lambda uri: print("fired:", uri), interval=30.0)
# ... later
life.reminders.stop()
```

## Your first voice command

The voice gateway is the single entry point for any voice-assistant
request — Alexa, Siri, Cortana, or Google Home. You wire it up once with the
three platform subsystems (memory, life, agents); it parses the
assistant-specific request, routes it to a built-in intent handler, and
returns a response in the assistant's format.

```python
from selma.memory import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph
from selma.life import LifeAssistant
from selma.agents import AgentsAssistant
from selma.voice import VoiceGateway
from pyoxigraph import NamedNode

memory = MemoryAPI(EmbeddedOxigraph())
life = LifeAssistant(memory, stated_by=NamedNode("https://selma.example/ns/core#self"))
agents = AgentsAssistant(memory, stated_by=NamedNode("https://selma.example/ns/core#self"))

gateway = VoiceGateway(memory, life, agents)

# An Alexa-format RememberIntent request.
request = {
    "request": {
        "intent": {
            "name": "RememberIntent",
            "slots": {
                "subject":   {"value": "http://example/alice"},
                "predicate": {"value": "http://example/knows"},
                "object":    {"value": "http://example/bob"},
            },
        },
    },
}

response = gateway.handle("alexa", request)
print(response)
```

Output:

```python
{
    "response": {
        "outputSpeech": {"type": "PlainText", "text": "Remembered."},
        "card": {"subject": "http://example/alice"},
    }
}
```

The nine built-in intents are `RememberIntent`, `RecallIntent`,
`DescribeIntent`, `CreateReminderIntent`, `ListRemindersIntent`,
`CreateTaskIntent`, `ListTasksIntent`, `StartActivityIntent`, and
`StopActivityIntent`. Use the assistant type strings `"alexa"`, `"siri"`,
`"cortana"`, and `"google"` to switch request/response formats.

## Running the test suite

```bash
pytest -v
```

The suite contains 206 tests covering all four sub-projects. A clean run ends
with:

```
========================= 206 passed =========================
```

## Next steps

- [Architecture](architecture.md) — how the four sub-projects fit together.
- API reference: [memory](api-reference/memory.md) · [life](api-reference/life.md)
  · [agents](api-reference/agents.md) · [voice](api-reference/voice.md)
- Tutorials: [Reminders & Scheduling](tutorials/01-reminders-and-scheduling.md)
  · [Custom Voice Intent](tutorials/02-custom-voice-intent.md)
  · [Custom Agent](tutorials/03-custom-agent.md)