# Voice Commands Cheat Sheet

Selma accepts voice commands through four assistants: **Alexa**, **Siri**,
**Cortana**, and **Google Home**. Each assistant sends requests in a different
JSON shape, but all nine built-in intents work across all four. This page is a
quick-reference for developers integrating a voice skill or cloud function with
the `VoiceGateway`.

For a deeper look at the gateway internals, see the
[voice API reference](api-reference/voice.md).

## Assistant request formats

Each adapter flattens the assistant-specific request into a common
`VoiceRequest(intent, slots)` and translates the `VoiceResponse` back into the
assistant's native shape. The four formats are:

### Alexa

```json
{
  "request": {
    "intent": {
      "name": "CreateReminderIntent",
      "slots": {
        "label": {"value": "call mom"},
        "time":  {"value": "2026-07-06T15:00:00"}
      }
    }
  }
}
```

Slots are a dict of `name → {"value": "..."}` objects. The response is
`{"response": {"outputSpeech": {"type": "PlainText", "text": "..."}, "card": {...}}}`.

### Siri

```json
{
  "intent": "CreateReminderIntent",
  "parameters": {
    "label": "call mom",
    "time": "2026-07-06T15:00:00"
  }
}
```

Slots are a flat `dict[str, str]` under `parameters`. The response is
`{"spokenResponse": "...", "content": {...}}`.

### Cortana

```json
{
  "intent": "CreateReminderIntent",
  "entities": [
    {"type": "label", "value": "call mom"},
    {"type": "time",  "value": "2026-07-06T15:00:00"}
  ]
}
```

Slots arrive as a list of `{"type": ..., "value": ...}` objects; the adapter
keys them by `type`. The response is `{"text": "...", "card": {...}}`.

### Google Home

```json
{
  "intent": "CreateReminderIntent",
  "params": {
    "label": "call mom",
    "time": "2026-07-06T15:00:00"
  }
}
```

Slots are a flat `dict[str, str]` under `params` (Dialogflow convention). The
response is `{"fulfillmentText": "...", "payload": {...}}`.

## Built-in intents

| Intent | Example phrase | Required slots | Sample response |
|--------|---------------|----------------|-----------------|
| `RememberIntent` | "Remember that Alice knows Bob" | `subject`, `predicate`, `object` | "Remembered." |
| `RecallIntent` | "What do you know about Alice?" | `subject` | "About `http://example/alice`: `http://example/knows` Bob." |
| `DescribeIntent` | "What can you do?" | — | "I can remember, recall, set reminders, list tasks, and track activities…" |
| `CreateReminderIntent` | "Remind me to call mom at 3pm" | `label`, `time` | "Reminder set: call mom at 2026-07-06T15:00:00." |
| `ListRemindersIntent` | "What are my reminders?" | — | "Your reminders: call mom at 2026-07-06T15:00:00." |
| `StartActivityIntent` | "I'm starting to write docs" | `label` | "Started activity: write docs." |
| `StopActivityIntent` | "Stop my activity" | — | "Activity stopped." |
| `CreateTaskIntent` | "Add a task to the website project" | `label`, `project` | "Task created: fix header." |
| `ListTasksIntent` | "What are my open tasks for the website project?" | `project` | "Your open tasks: fix header; add footer." |

## Slot format reference

| Slot type | Format | Example |
|-----------|--------|---------|
| URI | Full URI string | `http://example/alice` |
| Datetime | ISO 8601 (`YYYY-MM-DDTHH:MM:SS`) | `2026-07-06T15:00:00` |
| Literal text | Plain string | `call mom` |

### URI slots

`RememberIntent` and `RecallIntent` treat `subject` and `predicate` as URIs
and `object` as literal text:

```
subject   = "http://example/alice"
predicate = "http://example/knows"
object    = "Bob"
```

This stores the reified fact `<http://example/alice> <http://example/knows> "Bob"`
in memory with provenance metadata.

### Datetime slots

`CreateReminderIntent` expects `time` as an ISO 8601 datetime string. The
reminder scheduler compares this against the current UTC time.

```
time = "2026-07-06T15:00:00"
```

### Literal text slots

`label` (used by `CreateReminderIntent`, `StartActivityIntent`,
`CreateTaskIntent`) and `project` (used by `CreateTaskIntent`,
`ListTasksIntent`) are plain text strings passed directly to the underlying
service.

## Quick-start

```python
from selma.memory import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph
from selma.life import LifeAssistant
from selma.agents import AgentsAssistant
from selma.voice import VoiceGateway

memory = MemoryAPI(EmbeddedOxigraph())
life = LifeAssistant(memory)
agents = AgentsAssistant(memory)
gateway = VoiceGateway(memory, life, agents)

response = gateway.handle("alexa", {
    "request": {"intent": {
        "name": "CreateReminderIntent",
        "slots": {"label": {"value": "call mom"},
                  "time":  {"value": "2026-07-06T15:00:00"}}
    }}
})
print(response)
# {"response": {"outputSpeech": {"type": "PlainText",
#  "text": "Reminder set: call mom at 2026-07-06T15:00:00."},
#  "card": {"reminder": "https://selma.example/ns/life#reminder/..."}}}
```

See the [getting-started guide](getting-started.md) for the full walkthrough
and the [tutorials](tutorials/01-reminders-and-scheduling.md) for deeper
examples.