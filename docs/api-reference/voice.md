# `selma.voice` API reference

`selma.voice` is the voice-assistant integration gateway. It translates the
request formats of four voice assistants (Alexa, Siri, Cortana, Google Home)
into a common internal shape, routes each request to a registered intent
handler, and translates the response back. It is a pure client of
`selma.memory`, `selma.life`, and `selma.agents`.

## Public exports

| Name | Kind | Description |
|------|------|-------------|
| `VoiceGateway` | class | Facade wiring router + adapters + subsystems. |
| `VoiceRouter` | class | Intent registry + dispatch with error mapping. |
| `register_builtin_intents` | function | Register the nine built-in handlers on a router. |
| `VoiceRequest` | dataclass | Assistant-independent request (intent name + slots). |
| `VoiceResponse` | dataclass | Assistant-independent reply (text + optional card). |
| `VoiceContext` | dataclass | References to the three Selma subsystems. |
| `AlexaAdapter` | class | Alexa-format request/response transform. |
| `SiriAdapter` | class | Siri-format request/response transform. |
| `CortanaAdapter` | class | Cortana-format request/response transform. |
| `GoogleHomeAdapter` | class | Google Home / Dialogflow-format transform. |
| `VoiceError` | exception | Base class for all `selma.voice` errors. |
| `UnknownIntentError` | exception | `dispatch` called with an intent that has no handler. |
| `MissingSlotError` | exception | A handler required a slot not in the request. |
| `UnknownAssistantError` | exception | `handle` called with an assistant type that has no adapter. |

## `VoiceGateway`

```python
VoiceGateway(memory: MemoryAPI, life: LifeAssistant, agents: AgentsAssistant) -> None
```

The single entry point for a transport layer (HTTP skill handler, Cloud
Function, etc.). It wires a `VoiceRouter` over a `VoiceContext` holding the
three subsystems, registers the built-in intents, and holds the four
adapters.

| Method | Signature | Returns | Raises |
|--------|-----------|---------|--------|
| `handle` | `handle(assistant_type: str, request: dict) -> dict` | assistant-format response dict | `UnknownAssistantError` |

`handle` parses the request via the adapter, dispatches the intent, and
returns the response in the assistant's format. Unknown `assistant_type`
raises `UnknownAssistantError` (there is no adapter to format a response
with). Handler-side failures are mapped by the router to friendly
`VoiceResponse` messages and never raise out of `handle`.

### Example

```python
from selma.memory import MemoryAPI, EmbeddedOxigraph
from selma.life import LifeAssistant
from selma.agents import AgentsAssistant
from selma.voice import VoiceGateway

gw = VoiceGateway(MemoryAPI(EmbeddedOxigraph()),
                  LifeAssistant(MemoryAPI(EmbeddedOxigraph())),
                  AgentsAssistant(MemoryAPI(EmbeddedOxigraph())))
resp = gw.handle("alexa", {
    "request": {"intent": {
        "name": "CreateReminderIntent",
        "slots": {"label": {"value": "call mom"},
                  "time":  {"value": "2026-07-06T15:00:00"}}}}})
print(resp)  # {"response": {"outputSpeech": {...}, "card": {"reminder": uri}}}
```

## `VoiceRouter`

```python
VoiceRouter(context: VoiceContext) -> None
```

Registry of intent name → handler callable. Handlers have the signature
`handler(slots: dict[str, str], context: VoiceContext) -> VoiceResponse`.

| Member | Signature | Returns |
|--------|-----------|---------|
| `context` | property | `VoiceContext` |
| `register` | `register(intent: str, handler) -> None` | — |
| `dispatch` | `dispatch(intent: str, slots: dict[str, str]) -> VoiceResponse` | `VoiceResponse` |

`dispatch` error mapping (spec §7):

- unknown intent → `VoiceResponse("I don't know how to do that yet")`
- `MissingSlotError` → `VoiceResponse(f"I need a {slot_name} to do that")`
- any other handler exception → `VoiceResponse("Something went wrong")`

### Example

```python
from selma.voice import VoiceRouter, register_builtin_intents
from selma.voice.models import VoiceContext

# ctx is a VoiceContext built from the three subsystems
router = VoiceRouter(ctx)
register_builtin_intents(router)
resp = router.dispatch("RecallIntent", {"subject": "http://ex/alice"})
print(resp.response_text)
```

## `register_builtin_intents`

```python
register_builtin_intents(router: VoiceRouter) -> None
```

Registers the nine built-in intent handlers on `router`:

| Intent name | Handler | Required slots |
|-------------|---------|----------------|
| `RememberIntent` | `handle_remember` | `subject`, `predicate`, `object` |
| `RecallIntent` | `handle_recall` | `subject` |
| `DescribeIntent` | `handle_describe` | — |
| `CreateReminderIntent` | `handle_create_reminder` | `label`, `time` |
| `ListRemindersIntent` | `handle_list_reminders` | — |
| `StartActivityIntent` | `handle_start_activity` | `label` |
| `StopActivityIntent` | `handle_stop_activity` | — |
| `CreateTaskIntent` | `handle_create_task` | `label`, `project` |
| `ListTasksIntent` | `handle_list_tasks` | `project` |

Each handler is a plain function that extracts the slots it needs (via
`require_slots` where a slot is mandatory), calls the relevant Selma
subsystem, and builds a `VoiceResponse`.

## Adapters

Each adapter is a stateless transform with two methods. No I/O, no network,
no state.

| Method | Signature | Returns | Raises |
|--------|-----------|---------|--------|
| `parse_request` | `parse_request(request: dict) -> VoiceRequest` | `VoiceRequest` | `UnknownIntentError` |
| `format_response` | `format_response(response: VoiceResponse) -> dict` | assistant-format dict | — |

### `AlexaAdapter`

Alexa format. Request: `request.intent.name` + `request.intent.slots` (a
dict of slot name → `{"value": ...}`). Response:
`response.outputSpeech.text` (`{"type": "PlainText"}`) plus optional
`response.card`.

### `SiriAdapter`

Siri format. Request: `intent` + `parameters` (`dict[str, str]`). Response:
`spokenResponse` plus optional `content`.

### `CortanaAdapter`

Cortana format. Request: `intent` + `entities` (a list of
`{"type": ..., "value": ...}` dicts; flattened into the slots dict keyed by
`type`). Response: `text` plus optional `card`.

### `GoogleHomeAdapter`

Google Home / Dialogflow format. Request: `intent` + `params`
(`dict[str, str]`). Response: `fulfillmentText` plus optional `payload`.

### Example

```python
from selma.voice import AlexaAdapter, VoiceResponse

ad = AlexaAdapter()
vr = ad.parse_request({"request": {"intent": {
    "name": "DescribeIntent", "slots": {}}}})
print(vr.intent)                       # "DescribeIntent"
print(ad.format_response(VoiceResponse("hi", card={"k": "v"})))
# {"response": {"outputSpeech": {"type": "PlainText", "text": "hi"}, "card": {"k": "v"}}}
```

## Dataclasses

### `VoiceRequest`

```python
@dataclass
class VoiceRequest:
    intent: str
    slots: dict[str, str] = field(default_factory=dict)
```

### `VoiceResponse`

```python
@dataclass
class VoiceResponse:
    response_text: str
    card: dict | None = None
```

### `VoiceContext`

```python
@dataclass
class VoiceContext:
    memory: "MemoryAPI"
    life: "LifeAssistant"
    agents: "AgentsAssistant"
```

References to the three Selma subsystems, passed to every intent handler.
(`VoiceContext` is also importable from `selma.voice.context`.)

## Exceptions

| Exception | When raised |
|-----------|-------------|
| `VoiceError` | Base class for all `selma.voice` errors (subclass of `MemoryError`). |
| `UnknownIntentError` | `dispatch` called with an intent that has no registered handler; also by an adapter when a request has no intent name. |
| `MissingSlotError` | A handler required a slot not in the request. Carries the slot name on `.slot_name`. |
| `UnknownAssistantError` | `VoiceGateway.handle` called with an assistant type that has no adapter. |

## Cross-references

- Architecture overview: [../architecture.md](../architecture.md)
- Memory API reference: [memory.md](memory.md)
- Life API reference: [life.md](life.md)
- Agents API reference: [agents.md](agents.md)
- Design spec: [../superpowers/specs/2026-07-06-selma-voice-design.md](../superpowers/specs/2026-07-06-selma-voice-design.md)