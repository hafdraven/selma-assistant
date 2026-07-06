# Selma Architecture

This document describes how the four Selma sub-projects relate, how data flows
through the platform, and the key design decisions behind them. For the full
rationale behind each subsystem, see the design specs linked at the end.

## Platform overview

Selma is a Jarvis/Time-Trax-style life-assistant agent platform. The original
vision is a single assistant that remembers everything about your life,
manages your schedule, executes tasks on its own, and talks to you through
whichever voice assistant you happen to be using.

The platform is structured as four sub-projects, each a pure Python package
with a narrow public surface:

| Sub-project | Package | Role |
|-------------|---------|------|
| **memory** | `selma.memory` | RDF/SPARQL semantic memory core; the foundation everything else builds on |
| **life** | `selma.life` | Reminders, scheduling, and activity tracking |
| **agents** | `selma.agents` | Projects, tasks, coordination, and autonomous task execution |
| **voice** | `selma.voice` | Voice-assistant gateway (Alexa, Siri, Cortana, Google Home) |

The dependency direction is strictly top-down: `voice` depends on `life`,
`agents`, and `memory`; `life` and `agents` depend only on `memory`; `memory`
depends on nothing inside Selma. No sub-project imports upward.

## Dependency graph

```
┌─────────────────────────────────────────────────────────┐
│                    selma.voice                           │
│  (Alexa / Siri / Cortana / Google Home adapters)        │
└────────────┬──────────────────────────┬─────────────────┘
             │                          │
┌────────────▼──────────┐  ┌───────────▼──────────────┐
│     selma.life        │  │     selma.agents          │
│  (reminders,          │  │  (projects, tasks,        │
│   scheduling,         │  │   coordination,           │
│   activities)         │  │   autonomous execution)   │
└────────────┬──────────┘  └───────────┬──────────────┘
             │                          │
             └──────────┬───────────────┘
                        │
             ┌──────────▼──────────┐
             │    selma.memory     │
             │  (RDF/SPARQL core,  │
             │   ontology, typed   │
             │   API, embedded     │
             │   Oxigraph backend) │
             └─────────────────────┘
```

## The memory core (`selma.memory`)

`selma.memory` is the semantic foundation of the platform. It stores every
piece of knowledge as an RDF reified fact and exposes it through a typed
Python API backed by an embedded Oxigraph triplestore.

### RDF reification model

Every fact is a blank node (`_:factNNN`) that reifies a single
(subject, predicate, object) triple using the standard RDF reification
vocabulary — `rdf:subject`, `rdf:predicate`, `rdf:object` — and attaches
temporal and provenance metadata:

| Metadata property | Meaning |
|-------------------|---------|
| `selma:recordedAt` | When the fact was stored |
| `selma:validFrom` | Start of the window in which the fact holds |
| `selma:validTo` | End of the window (unset = currently true) |
| `selma:statedBy` | The agent or source that asserted it (required) |
| `selma:confidence` | Decimal in [0, 1] |
| `selma:source` | URI or literal identifying the channel |
| `selma:supersedes` | Links a new fact to the one it replaces |

Because metadata lives on the reification node, two facts about the same
subject keep independent validity windows and provenance.

### Custom ontology

The core ontology lives in `selma.memory.ontology` and is self-describing —
`MemoryAPI.describe()` returns the full class and property list. It defines
**9 classes** and **18 properties**:

- **Classes**: `Entity`, `Agent`, `Event`, `Task`, `Project`, `Relationship`,
  `Fact`, `Belief`, `Reminder` (a subclass of `Event`).
- **Properties**: `recordedAt`, `validFrom`, `validTo`, `statedBy`,
  `confidence`, `source`, `label`, `description`, `tag`, `relates`,
  `relatedBy`, `partOf`, `dependsOn`, `supersedes`, `hasStatus`, `ownedBy`,
  `dueBy`, `completedAt`.

### Backend Protocol

Every storage backend honors the `Backend` Protocol in
`selma.memory.backends.protocol` — `begin`/`commit`/`rollback`,
`add`/`remove`, `query`, `update`, `count`, `close`. The default and only
implemented backend is `EmbeddedOxigraph`, an in-process pyoxigraph store
that can run in RAM or persist to a directory on disk. The `get_backend`
factory selects a backend from a `BackendConfig`; `remote` (a remote
triplestore) and `managed` (a managed RDF service) backends are stubbed for
future work.

### Typed API

`MemoryAPI` wraps a backend with a typed surface:

| Method | Purpose |
|--------|---------|
| `remember(subject, predicate, obj, *, stated_by, …)` | Store a reified fact with provenance |
| `recall(subject?, predicate?, obj?, *, as_of?, include_history?)` | Read current (or historical) facts |
| `find(class_uri, *, filters?, as_of?)` | Discover instances of a class |
| `relate(subject, predicate, obj, *, stated_by, …)` | Store a relationship (inverse-aware) |
| `supersede(fact_uri, new_value, *, stated_by, reason?)` | Retire an old fact and assert a replacement |
| `forget(subject?, predicate?, obj?, *, soft=True, reason?)` | Soft-delete (set `validTo`) or hard-delete with audit |
| `ask(sparql_str, *, bindings?)` | Passthrough SPARQL (routes UPDATE vs SELECT) |
| `describe()` | Return the ontology self-description |

### Light entailment

`selma.memory.entailment` provides three query-time entailment expansions —
no reasoner, no materialization. `subclass_expand` widens a class to its
transitive subclasses, `inverse_of` returns the `owl:inverseOf` partner of a
property, and `is_transitive` flags `partOf` and `dependsOn` so SPARQL
builders can emit property paths (`partOf+`).

## The life-assistant core (`selma.life`)

`selma.life` is a pure client of `selma.memory`. The `LifeAssistant` facade
exposes three services, each storing its data as reified facts through
`MemoryAPI`:

- **`ReminderService`** — `create(fire_at, *, about?, label?)`, `list(*, due_before?, include_fired?)`, `fire(uri)`, `check_due()`, and a polling scheduler (`start(callback, *, interval=30.0)` / `stop()`).
- **`ScheduleService`** — `create(start, end, *, label?, part_of?)` with conflict detection, `move(uri, new_start, *, new_end?)`, `cancel(uri)`, `list(*, day? | week?)`, `conflicts(start, end, *, exclude?)`.
- **`ActivityService`** — `start(label, *, tags?, part_of?, at?)`, `stop(uri, *, at?)`, `current()`, `history(*, since?, until?, tags?)`. v1 enforces a single running activity.

Every entity is stored in two steps: a type assertion (`<uri> a selma:Reminder`) inserted into the `selma:default` named graph so `find()` discovers it, followed by reified property facts (`validFrom`, `label`, etc.) in the default graph via `remember`. Single-valued lifecycle facts are retired with `forget(soft=True)` plus a fresh `remember`, preserving history.

The reminder scheduler is a daemon `threading.Timer` that polls `check_due`
on a fixed interval, fires any due reminders through the caller's callback,
and re-arms itself. It is idempotent: a `FILTER NOT EXISTS { ?r life:firedAt ?f }` guard prevents double-firing.

## The agents core (`selma.agents`)

`selma.agents` is a pure client of `selma.memory`. The `AgentsAssistant`
facade exposes four services:

- **`ProjectService`** — `create(label, *, description?, part_of?)`, `get(uri)`, `list()`.
- **`TaskService`** — `create(label, *, project?, description?, owner?, due_by?, depends_on?)`, `get(uri)`, `list(*, project?)`, `set_status(uri, status)`, `set_owner(uri, owner)`, `add_dependency(uri, depends_on)`, `dependencies(uri)`.
- **`TaskCoordinator`** — project-scoped views and status transitions: `open_tasks(project)`, `blocked_tasks(*, project?)`, `blockers(uri)`, `claim(uri, *, owner)`, `complete(uri)`, `block(uri, *, reason)`. Allowed transitions: `open → in_progress/blocked`, `in_progress → done/blocked`, `blocked → in_progress/open`, `done → ∅`.
- **`AgentRunner`** — `run(task_uri, executor)` where `executor` is a `Callable[[str, MemoryAPI], str]`. It claims the task, runs the executor, and on success records `agents:executionResult` and marks the task `done`; on exception it marks the task `blocked` with the error message and re-raises. v1 is sequential (one task per `run` call).

Tasks and projects use the same two-step storage pattern as life entities: a type assertion in the named graph plus reified property facts. Single-valued lifecycle facts (`hasStatus`, `ownedBy`) are mutated with soft-forget + remember so the full history of status changes is retained.

## The voice gateway (`selma.voice`)

`selma.voice` is a pure client of all three other sub-projects. Its job is to
translate the four voice assistants' request formats into a common internal
shape, route to the right handler, and translate the response back.

### Components

- **`VoiceGateway(memory, life, agents)`** — the facade. Its single method `handle(assistant_type, request_dict) -> dict` parses the request via the adapter, dispatches the intent, and returns the formatted response. Unknown assistant types raise `UnknownAssistantError`; handler errors never escape `handle`.
- **`VoiceRouter`** — a registry of intent name → handler callable. `dispatch(intent, slots)` looks up the handler and maps three failure cases to fixed friendly messages: unknown intent, missing required slot, and any other exception.
- **Adapters** — `AlexaAdapter`, `SiriAdapter`, `CortanaAdapter`, `GoogleHomeAdapter`. Each is a stateless transform with `parse_request(dict) -> VoiceRequest` and `format_response(VoiceResponse) -> dict`.
- **Built-in intents** — nine handlers registered by `register_builtin_intents`: `RememberIntent`, `RecallIntent`, `DescribeIntent`, `CreateReminderIntent`, `ListRemindersIntent`, `CreateTaskIntent`, `ListTasksIntent`, `StartActivityIntent`, `StopActivityIntent`.

## Data flow walkthrough

A user says "remind me to call mom at 3pm" to an Alexa device. The Alexa
skill sends a request to the transport layer, which calls the gateway:

1. **Alexa adapter** parses the raw request into a `VoiceRequest(intent="CreateReminderIntent", slots={"label": "call mom", "time": "2026-07-06T15:00:00"})`.
2. **`VoiceRouter.dispatch`** looks up the `CreateReminderIntent` handler and calls it with the slots and the `VoiceContext` (which holds references to `memory`, `life`, and `agents`).
3. The handler calls `ctx.life.reminders.create("2026-07-06T15:00:00", label="call mom")`.
4. `ReminderService.create` inserts a type assertion (`<uri> a selma:Reminder`) into the `selma:default` named graph, then calls `MemoryAPI.remember` twice — once for `validFrom` (the fire time) and once for `label`.
5. `MemoryAPI.remember` builds a SPARQL `INSERT DATA` with a blank reification node (`_:factNNN`) carrying `rdf:subject`, `rdf:predicate`, `rdf:object`, plus `selma:statedBy`, `selma:recordedAt`, and `selma:validFrom`, and sends it to `EmbeddedOxigraph.update`.
6. **Oxigraph** persists the quads.
7. The handler returns `VoiceResponse("Reminder set: call mom at 2026-07-06T15:00:00.", card={"reminder": uri})`.
8. **`VoiceRouter`** returns the response to the gateway.
9. **Alexa adapter** formats it as `{"response": {"outputSpeech": {"type": "PlainText", "text": "Reminder set: call mom at 2026-07-06T15:00:00."}, "card": {"reminder": uri}}}`.
10. The transport layer sends that dict back to Alexa, which speaks the text.

## Design decisions summary

| Decision | Rationale |
|----------|-----------|
| **RDF reification over plain triples** | Attaching provenance and temporal metadata to the *fact* rather than the subject lets multiple facts about the same entity coexist with independent validity windows. |
| **Blank-node reification, not RDF-star** | Keeps the model portable across any SPARQL 1.1 triplestore, including embedded Oxigraph, without requiring RDF-star support. |
| **Soft-delete by default** | `forget(soft=True)` sets `validTo = now`, so facts drop out of the current view but remain in history. Hard deletes require an explicit reason and log to an audit graph. |
| **Soft-forget + remember for mutations** | `supersede` is ambiguous for multi-fact subjects (it picks the first predicate regardless of intent). Lifecycle mutations retire the old fact with a targeted `forget(soft=True)` and assert a fresh one. |
| **In-process Oxigraph backend** | Zero-ops persistence for a personal assistant; the `Backend` Protocol keeps the door open for remote and managed backends without changing the API. |
| **Typed API over raw SPARQL** | `remember`/`recall`/`find`/`forget` give callers a safe, provenance-required surface while `ask` remains an escape hatch for arbitrary SPARQL. |
| **Stateless voice adapters** | Each adapter is a pure transform with no I/O or state, so the gateway is trivially testable and the assistant formats are decoupled from intent logic. |
| **Sequential agent runner** | v1 runs one task per `run` call with no parallelism or queue, keeping the execution model simple and deterministic. |

## Further reading

Design specs (in `docs/superpowers/specs/`):

- [Memory Core Design](superpowers/specs/2026-07-05-selma-memory-core-design.md)
- [Life Design](superpowers/specs/2026-07-06-selma-life-design.md)
- [Agents Design](superpowers/specs/2026-07-06-selma-agents-design.md)
- [Voice Design](superpowers/specs/2026-07-06-selma-voice-design.md)

API reference: [memory](api-reference/memory.md) · [life](api-reference/life.md)
· [agents](api-reference/agents.md) · [voice](api-reference/voice.md)