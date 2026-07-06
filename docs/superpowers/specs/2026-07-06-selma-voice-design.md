# Selma Voice — Voice-Assistant Integration Gateway Design

**Date:** 2026-07-06
**Status:** Approved (design sections)
**Sub-project:** `selma.voice` — voice-assistant integration gateway
**Spec language:** English

---

## 1. Scope & Position in the Platform

This spec covers **`selma.voice`**, the fourth and final sub-project of the Selma
assistant platform. It is a voice-assistant integration gateway that routes intents
from voice assistants (Alexa, Siri, Cortana, Google Home) into the three Selma
platform subsystems already in place:

- `selma.memory` — the RDF/SPARQL memory core (`MemoryAPI`).
- `selma.life` — the life-assistant core (`LifeAssistant`).
- `selma.agents` — the autonomous task-execution core (`AgentsAssistant`).

`selma.voice` is a pure client of those three subsystems. It adds no new storage and
no new domain logic; it only translates between voice-assistant request/response
formats and Selma platform actions.

### What this subsystem does

- Defines a declarative **intent schema**: a mapping from a voice-assistant intent
  name to a handler callable that calls `MemoryAPI` / `LifeAssistant` /
  `AgentsAssistant`.
- Provides a **`VoiceRouter`**: validates slot values, dispatches the intent to the
  registered handler, and returns a `VoiceResponse` (what the assistant says back).
- Provides **voice adapters** (`AlexaAdapter`, `SiriAdapter`, `CortanaAdapter`,
  `GoogleHomeAdapter`) that translate each assistant's request format into a common
  `VoiceRequest` and a common `VoiceResponse` back into the assistant's response
  format. The adapters are pure data-structure transformations — no I/O, no
  network.
- Ships a set of **built-in intents** covering the common life/memory/agents
  operations.
- Provides a **`VoiceGateway`** facade that wires the router, the adapters, and the
  three platform subsystems together behind one `handle(assistant_type,
  request_dict)` method.

### What this subsystem does NOT do (out of scope)

- It does not connect to real voice-assistant SDKs or cloud endpoints. The adapters
  transform representative request/response data structures only. A later
  deployment sub-project will plug real SDK transport underneath these formats.
- It does not do natural-language understanding. Mapping spoken user utterances to
  intent names + slot values is the voice assistant's own NLU; `selma.voice` starts
  where the assistant has already produced a structured intent.
- It does not own domain data. All state lives in `selma.memory` via the typed API.

### Package shape

A Python library (`selma.voice`) consumed directly by tests and, later, by a thin
HTTP/Skill transport layer. Public surface: `VoiceGateway`, `VoiceRouter`,
`VoiceRequest` / `VoiceResponse` / `VoiceContext`, the four adapters, the exception
hierarchy, and a registry of built-in intents.

---

## 2. Common Models

All cross-assistant data flows through three dataclasses defined in
`selma.voice.models`.

### `VoiceRequest`

```python
@dataclass
class VoiceRequest:
    intent: str                       # e.g. "RememberIntent"
    slots: dict[str, str] = field(default_factory=dict)
```

The assistant-independent representation of "the user wants to do X with these
parameters." `intent` is a string name; `slots` is a flat `dict[str, str]` of
parameter name → value. Adapters produce this; the router consumes it.

### `VoiceResponse`

```python
@dataclass
class VoiceResponse:
    response_text: str                # what the assistant should say
    card: dict | None = None          # optional visual card payload
```

The assistant-independent representation of the reply. `response_text` is always
present (even on errors). `card` is an optional dict carrying structured display
data the adapter may render into the assistant's card format.

### `VoiceContext`

```python
@dataclass
class VoiceContext:
    memory: MemoryAPI
    life: LifeAssistant
    agents: AgentsAssistant
```

Passed to every intent handler so it can reach the platform subsystems. Holds
references, owns no state.

---

## 3. Intent Router

### `VoiceRouter`

```python
class VoiceRouter:
    def __init__(self, context: VoiceContext) -> None: ...
    def register(self, intent: str, handler: Handler) -> None: ...
    def dispatch(self, intent: str, slots: dict[str, str]) -> VoiceResponse: ...
```

A handler is a callable with the signature:

```python
handler(slots: dict[str, str], context: VoiceContext) -> VoiceResponse
```

`dispatch`:

1. Looks up the handler for `intent`. Unknown intent →
   `VoiceResponse("I don't know how to do that yet")`.
2. Calls the handler inside a `try/except Exception`. Any handler exception →
   `VoiceResponse("Something went wrong")`.
3. Returns the `VoiceResponse`.

Slot validation (required-slot presence) is the handler's responsibility, but a
shared helper `require_slots(slots, *names)` raises `MissingSlotError` when a
required slot is absent; the router catches `MissingSlotError` specifically and
returns `VoiceResponse("I need a [slot name] to do that")` so handlers do not each
have to format that message.

### Built-in registry

`register_builtin_intents(router)` registers the nine built-in intents
(see §5) on a router. `VoiceGateway` calls this during construction.

---

## 4. Voice Adapters

Each adapter is a pure transformation class with two methods:

```python
class Adapter:
    def parse_request(self, request: dict) -> VoiceRequest: ...
    def format_response(self, response: VoiceResponse) -> dict: ...
```

No I/O, no network, no state. The four adapters differ only in the shape of the
request and response dicts they translate. The formats are simplified
representations of each assistant's SDK schema — enough to exercise the adapter
pattern without depending on any real SDK.

### `AlexaAdapter`

- **Request**: `request.intent.name` (str) and `request.intent.slots` (a dict of
  slot name → `{"value": ...}`). Missing intent → `UnknownIntentError`.
- **Response**: `{"response": {"outputSpeech": {"type": "PlainText", "text":
  <response_text>}, "card": <card or omitted>}}`.

### `SiriAdapter`

- **Request**: `intent` (str) and `parameters` (dict[str, str]).
- **Response**: `{"spokenResponse": <response_text>, "content": <card or None>}}`.

### `CortanaAdapter`

- **Request**: `intent` (str) and `entities` (a list of `{"type": ..., "value":
  ...}` dicts; the adapter flattens them into the slots dict keyed by `type`).
- **Response**: `{"text": <response_text>, "card": <card or None>}}`.

### `GoogleHomeAdapter`

- **Request**: `intent` (str) and `params` (dict[str, str]).
- **Response**: `{"fulfillmentText": <response_text>, "payload": <card or
  None>}}`.

---

## 5. Built-in Intents

Nine built-in intents route to the three subsystems. Each handler extracts the
slots it needs (using `require_slots` where a slot is mandatory), calls the
relevant service, and builds a `VoiceResponse`.

| Intent | Slots | Routes to | Response |
|--------|-------|-----------|----------|
| `RememberIntent` | `subject`, `predicate`, `object` | `memory.remember(...)` | "Remembered." + card with the subject URI |
| `RecallIntent` | `subject` | `memory.recall(subject=...)` | Lists known `(predicate, object)` pairs, or "I don't know anything about [subject] yet." |
| `CreateReminderIntent` | `label`, `time` | `life.reminders.create(...)` | "Reminder set: [label] at [time]." + card with the reminder URI |
| `ListRemindersIntent` | — | `life.reminders.list()` | Lists reminder labels/times, or "You have no reminders." |
| `CreateTaskIntent` | `label`, `project` | `agents.tasks.create(...)` | "Task created: [label]." + card with the task URI |
| `ListTasksIntent` | `project` | `agents.coordinator.open_tasks(project=...)` | Lists open task labels, or "You have no open tasks for [project]." |
| `StartActivityIntent` | `label` | `life.activities.start(...)` | "Started activity: [label]." + card with the activity URI |
| `StopActivityIntent` | — | `life.activities.stop(current.uri)` | "Activity stopped." or "You don't have a running activity." |
| `DescribeIntent` | — | `memory.describe()` | Summarizes the ontology class list. |

Notes on routing:

- `RememberIntent` uses `memory.remember` with `stated_by` defaulting to the
  Selma self agent (`https://selma.example/ns/core#self`), consistent with the
  other subsystems' `default_stated_by()`.
- `RecallIntent` passes the slot value as the subject. Because `recall` accepts a
  string subject and resolves it internally, the handler passes the raw string;
  empty results yield a friendly "don't know" message rather than an error.
- `CreateReminderIntent`'s `time` slot is an ISO datetime string passed straight
  to `life.reminders.create(fire_at=...)`.
- `CreateTaskIntent`'s `project` slot is a project URI; the handler passes it to
  `agents.tasks.create(label=..., project=...)`.
- `ListTasksIntent`'s `project` slot is a project URI passed to
  `agents.coordinator.open_tasks(project=...)`.
- `StopActivityIntent` calls `life.activities.current()`; if `None` it returns the
  "no running activity" message, otherwise it calls `stop(current.uri)`.

---

## 6. VoiceGateway Facade

```python
class VoiceGateway:
    def __init__(self, memory, life, agents) -> None: ...
    def handle(self, assistant_type: str, request: dict) -> dict: ...
```

Construction:

1. Builds a `VoiceContext(memory, life, agents)`.
2. Builds a `VoiceRouter(context)` and registers the built-in intents on it.
3. Holds an adapter map: `{"alexa": AlexaAdapter(), "siri": SiriAdapter(),
   "cortana": CortanaAdapter(), "google": GoogleHomeAdapter()}`.

`handle(assistant_type, request)`:

1. Looks up the adapter for `assistant_type`. Unknown type → raises
   `UnknownAssistantError`.
2. `adapter.parse_request(request)` → `VoiceRequest`.
3. `router.dispatch(request.intent, request.slots)` → `VoiceResponse`.
4. `adapter.format_response(response)` → assistant-format dict, returned to the
   caller.

The gateway is the single entry point for a transport layer (HTTP skill handler,
Cloud Function, etc.) that receives a raw assistant request and needs a raw
assistant response.

---

## 7. Error Handling

A small exception hierarchy in `selma.voice.exceptions`:

- `VoiceError` (base)
  - `UnknownIntentError` — `dispatch` called with an intent that has no handler.
  - `MissingSlotError` — a handler's `require_slots` check found a missing slot.
    Carries the slot name.
  - `UnknownAssistantError` — `VoiceGateway.handle` called with an assistant type
    that has no adapter.

Mapping (per the implementation brief):

- Unknown intent → `VoiceResponse("I don't know how to do that yet")` (the router
  catches `UnknownIntentError` itself; it also treats a missing registry entry as
  this case).
- Missing required slot → `VoiceResponse("I need a [slot name] to do that")`
  (the router catches `MissingSlotError`).
- Any other handler exception → `VoiceResponse("Something went wrong")` (the
  router catches `Exception`).

The gateway never raises out of `handle` for handler-side failures; it always
returns a well-formed assistant response dict carrying the friendly error text.
The only `handle`-side failure is an unknown `assistant_type`, which raises
`UnknownAssistantError` since there is no adapter to format a response with.

---

## 8. Testing

Four test modules in `tests/voice/`:

- `test_router.py` — registry + dispatch; unknown intent; missing slot; handler
  exception.
- `test_intents.py` — each built-in intent against a fresh `MemoryAPI` +
  `LifeAssistant` + `AgentsAssistant` stack (built in `tests/voice/conftest.py`
  on top of the shared `fresh_api` fixture).
- `test_adapters.py` — `parse_request` and `format_response` for all four
  adapters, including Alexa's nested slot shape and Cortana's entity-list shape.
- `test_gateway.py` — `handle` for each assistant type end-to-end, plus unknown
  assistant type.

The shared `tests/conftest.py` `fresh_api` fixture is reused; the voice conftest
builds `LifeAssistant` and `AgentsAssistant` on top of it.

---

## 9. Decisions Log

| Decision | Choice | Alternatives considered |
|----------|--------|-------------------------|
| Adapter scope | Pure data transformation, no I/O | Thin wrappers over real SDKs; full SDK emulation |
| Request/response common model | `VoiceRequest(intent, slots)` + `VoiceResponse(text, card)` dataclasses | Per-assistant handler signatures; a single typed union |
| Slot validation location | Shared `require_slots` helper raising `MissingSlotError`, caught by the router | Each handler formats its own message; validate in adapter |
| Handler error surface | Router catches all handler exceptions and returns a fixed friendly message | Propagate; per-exception messages |
| Assistant type key | Lowercase short names (`alexa`, `siri`, `cortana`, `google`) | Full product names; enum |
| Gateway failure mode | Unknown assistant type raises; handler failures return a response | Always return a response; always raise |