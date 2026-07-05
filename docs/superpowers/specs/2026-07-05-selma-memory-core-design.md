# Selma Memory Core — Design Spec

**Date:** 2026-07-05
**Status:** Approved (design sections) — pending user spec review
**Sub-project:** `selma.memory` — the semantic memory core of the Selma assistant platform
**Spec language:** English

---

## 1. Scope & Position in the Platform

This spec covers **`selma.memory`** — the semantic memory core of the Selma assistant
platform. It is the foundation subsystem; the other three (life-assistant, voice
integration, autonomous execution) will be designed later as separate sub-projects
that consume this one's contract.

The Selma platform is envisioned as a generic assistant agent platform that acts like
Jarvis (Iron Man) or Selma (Time Trax): it follows the user's life activities, reminds
and supports them, schedules their time, integrates with voice assistants (Alexa, Siri,
Cortana, Google Home), and coordinates autonomous execution of tasks across the user's
projects. All of those subsystems need a shared, queryable memory, and this spec defines
that memory.

### What this subsystem does

- Stores facts, events, tasks, projects, relationships, and beliefs as RDF triples in a
  pluggable backend (embedded Oxigraph first; self-hosted triplestore and managed cloud
  later, behind one interface).
- Owns a custom compact upper ontology (Entity, Event, Task, Project, Relationship, Fact,
  Belief, Agent, Reminder, plus reusable properties) and serves it to any client via a
  `/describe` endpoint as JSON-LD + natural-language descriptions.
- Provides a typed memory API (`remember`, `recall`, `find`, `relate`, `supersede`, etc.)
  that compiles to SPARQL internally, plus a passthrough SPARQL query method for power
  queries.
- Records provenance and confidence per statement, and timestamp/validity windows so any
  query can ask "as-of" a past time.
- Applies light RDFS/OWL entailment rules (subclass, inverseOf, transitive relations) at
  query time.

### What this subsystem does NOT do (out of scope, later sub-projects)

- Reminders, scheduling, or any life-assistant logic — those are clients of this layer.
  (The `Reminder` class exists to *store* reminders; firing/scheduling them is a later
  sub-project.)
- Voice-assistant integration (Alexa/Siri/Cortana/Google Home) intent routing.
- Autonomous task execution or project coordination agents.
- Natural-language understanding; the LLM/agent that turns user input into memory API
  calls lives outside this subsystem.

### Package shape

A Python library (`selma.memory`) plus a thin optional HTTP wrapper
(`selma.memory.service`) that exposes the same typed API + `/describe` + passthrough
SPARQL over HTTP for non-Python clients. The wrapper is added after the library is solid,
but its interface is fixed now so the contract is stable.

---

## 2. Custom Compact Upper Ontology

The ontology is the contract every client (LLM, voice router, autonomous agent) learns via
`/describe`. It is small, life-domain-tailored, and linked-data friendly.

Namespace: `https://selma.example/ns/core#` (prefix `selma:`).

### Core classes

| Class | Purpose |
|-------|---------|
| `selma:Entity` | Top class. Anything that can be named and referenced: a person, place, object, organization, file, account. |
| `selma:Agent` | Subclass of `Entity` that can act: a person, an LLM, a voice assistant, an autonomous worker. |
| `selma:Event` | Something that happened or will happen, anchored in time (start/end). A meeting, a reminder firing, a task status change. |
| `selma:Task` | A unit of work: has status (open/in_progress/done/blocked), owner (Agent), optional deadline, optional parent Task or Project. |
| `selma:Project` | A container of Tasks and other resources; tracks goals and outcomes. Subclass of `Entity`. |
| `selma:Relationship` | A reified relationship between two Entities with type, start, end, provenance. Models e.g. "Alice —worked-for→ Bob (2020–2023)". |
| `selma:Fact` | A statement the assistant believes is true about the world, with provenance and confidence. Distinct from `Belief`. |
| `selma:Belief` | A statement an Agent holds that may be uncertain, contested, or evolving — higher-level than `Fact`. |
| `selma:Reminder` | An `Event` subclass that fires at a time and produces a notification; links to the Task/Event it reminds about. |

### Reusable properties

Temporal:
- `selma:recordedAt` — when this statement was stored.
- `selma:validFrom` / `selma:validTo` — the time window in which the statement is held to
  be true.

Provenance & trust:
- `selma:statedBy` — the Agent or source that asserted this (required on every `Fact`).
- `selma:confidence` — `xsd:decimal` in [0, 1].
- `selma:source` — URI or literal identifying the channel ("voice:alexa",
  "agent:coordinator", "rule:inverseOf").

Metadata (used by `/describe` for NL rendering):
- `selma:label`, `selma:description`, `selma:tag`.

Structural:
- `selma:relates`, `selma:partOf`, `selma:dependsOn`, `selma:supersedes`.

Task lifecycle:
- `selma:hasStatus`, `selma:ownedBy`, `selma:dueBy`, `selma:completedAt`.

### Linked-data hooks

Where a public vocabulary already covers a concept well, the ontology links out rather
than reinventing:
- `selma:Agent` ↔ `foaf:Agent`
- `selma:Event` ↔ `schema:Event`
- People's names via `foaf:name`
- Task deadlines via `ical:due`

The custom core stays small; public vocabularies extend it. The `/describe` output
includes these cross-vocabulary links so clients can resolve them.

### Entailment rules (applied at query time, no full reasoner)

- `rdfs:subClassOf` — querying for `selma:Entity` returns `selma:Agent`, `selma:Project`,
  etc.
- `owl:inverseOf` — if `relates` is inverse of `relatedBy`, querying either returns both
  directions.
- `owl:TransitiveProperty` — `selma:partOf`, `selma:dependsOn` propagate transitively.

No full OWL reasoner. Anything beyond these three rule kinds is the calling client's job
(see "Reasoning load" decision).

---

## 3. Storage Backend Layer

The store is pluggable behind a single interface so the embedded store can be swapped for
a self-hosted triplestore or managed cloud service without touching the ontology or the
typed API.

### Backend interface

```python
class Backend(Protocol):
    def begin(self) -> Txn: ...                       # transaction handle
    def commit(self, txn) -> None: ...
    def rollback(self, txn) -> None: ...
    def add(self, txn, s, p, o, ctx=None) -> None: ...        # insert quad
    def remove(self, txn, s, p, o, ctx=None) -> None: ...    # delete quad
    def query(self, sparql: str, bindings: dict) -> QueryResult: ...  # SELECT/ASK/CONSTRUCT
    def update(self, sparql: str, bindings: dict) -> None: ...         # INSERT/DELETE
    def count(self, s, p, o, ctx=None) -> int: ...
    def close(self) -> None: ...
```

All operations are quad-based: the fourth element `ctx` is a named graph URI recording
*who asserted this batch* (the provenance source). This makes provenance queries trivial:
`GRAPH <source:voice-alexa> { ... }`.

### Three backend implementations, one interface

| Backend | When to use | Library |
|---------|-------------|---------|
| `EmbeddedOxigraph` (default) | Local dev, single-user assistant on a laptop, fast startup, transactional, in-process. | `oxigraph` PyPI |
| `RemoteTriplestore` | Self-hosted Fuseki/GraphDB/Oxigraph-server when you need shared access or scale beyond one machine. | SPARQL 1.1 over HTTP |
| `ManagedRDF` | Managed Neptune/Stardog when you want zero ops in production. | vendor SDK / SPARQL endpoint |

Only `EmbeddedOxigraph` is implemented in this sub-project. `RemoteTriplestore` and
`ManagedRDF` are stubbed behind the same interface so a later sub-project can fill them in
without touching the typed API.

### Backend selection & migration

- The backend is selected by config (`selma.memory.config.BackendConfig`); the rest of the
  code never imports a concrete backend.
- Switching backends is one config change, plus a one-time `dump`/`load` using N-Quads
  serialization to move data between backends.

### Persistence

- Embedded store writes to a local directory (`~/.selma/memory/` by default), durable
  across restarts.
- N-Quads is the canonical import/export format, so backups and migrations are plain file
  copies.

---

## 4. Typed Memory API + `/describe`

Clients talk to memory through the **typed API** (preferred) or **passthrough SPARQL** (for
complex queries). The `/describe` endpoint serves the ontology to any client so it can
construct its own calls.

### Typed API (`selma.memory.api.MemoryAPI`)

```python
remember(subject, predicate, obj, *, stated_by, confidence=1.0,
         valid_from=None, valid_to=None, source=None) -> Fact
recall(subject=None, predicate=None, obj=None, *, as_of=None,
       include_history=False) -> list[Binding]
find(class_uri, *, filters=None, as_of=None) -> list[Entity]
relate(subject, predicate, obj, *, stated_by, valid_from, valid_to) -> Relationship
supersede(fact_uri, new_value, *, stated_by, reason=None) -> Fact
forget(subject=None, predicate=None, obj=None, *, soft=True) -> int
ask(sparql: str, bindings: dict | None = None) -> QueryResult   # passthrough
describe() -> OntologyDescription
```

Semantics:
- `remember` inserts a quad with temporal + provenance metadata.
- `recall` runs a SELECT with filters, with optional `as_of` time-point semantics and
  optional history inclusion.
- `supersede` marks a fact as `validTo=now` and asserts a new one — the old fact is
  retained (visible to time-window queries), never deleted.
- `forget(soft=True)` sets `validTo=now` (logical delete); `forget(soft=False)` physically
  removes the quad (guarded; requires a reason, and is logged to the audit graph first).
- `ask` is the passthrough SPARQL escape hatch.

### `/describe` self-description

`describe()` returns (and the HTTP service later serves at `GET /describe`) an
`OntologyDescription`:

```json
{
  "context": { "selma": "https://selma.example/ns/core#", "foaf": "...", ... },
  "classes": [
    { "uri": "selma:Entity", "label": "Entity",
      "description": "Top class for anything named and referenceable.",
      "superclasses": [], "properties": ["selma:label", "selma:description"] },
    { "uri": "selma:Agent", "label": "Agent",
      "description": "An Entity that can act on Tasks or assert Facts.",
      "superclasses": ["selma:Entity"], "properties": ["..."] }
  ],
  "properties": [
    { "uri": "selma:recordedAt", "label": "recorded at",
      "description": "When this statement was stored.",
      "domain": "selma:Fact", "range": "xsd:dateTime" }
  ],
  "entailment_rules": [ "rdfs:subClassOf", "owl:inverseOf", "owl:TransitiveProperty" ],
  "example_queries": [
    "SELECT ?task WHERE { ?task a selma:Task ; selma:hasStatus 'open' . }"
  ]
}
```

### Client usage flow

1. Call `describe()` (or `GET /describe`) to get the ontology + vocabulary + examples.
2. For common cases: call typed API methods (no SPARQL needed).
3. For complex cases: build SPARQL using the vocabulary learned from `describe()`, call
   `ask()`.

### HTTP service wrapper (added later; interface fixed now)

- `POST /memory/remember`, `/memory/recall`, `/memory/find`, `/memory/relate`,
  `/memory/supersede`, `/memory/forget` — JSON body maps to the typed API.
- `POST /memory/ask` — passthrough SPARQL body.
- `GET /describe` — ontology document.
- All endpoints accept/return JSON-LD.

---

## 5. Error Handling

Every store-touching operation runs inside a transaction. Failures map to a small, explicit
exception hierarchy so clients can react without parsing strings:

- `MemoryError` (base)
  - `BackendError` — store unreachable / disk full / connection lost. Retriable for
    `RemoteTriplestore`/`ManagedRDF`; fatal for embedded.
  - `TransactionError` — commit/rollback failed (e.g. concurrent write conflict on a shared
    triplestore).
  - `QueryError` — malformed SPARQL or unknown prefix. Carries the offending query.
  - `OntologyError` — a typed-API call references an unknown class/property URI, or a
    value violates a range/domain constraint. Caught before hitting the store.
  - `ProvenanceError` — `remember`/`supersede` called without `stated_by` (required;
    nothing enters memory without a source).
  - `SupersedeError` — superseding a fact that was already superseded, or whose `validTo`
    is already set.

Rules:
- Nothing is ever silently dropped. A failed `remember` raises; partial writes are rolled
  back by the transaction.
- `forget(soft=False)` (hard delete) requires a `reason` argument and is logged to an
  audit graph (`<selma:audit>` named graph) before removal, so even hard deletes are
  traceable.
- `supersede` refuses to chain — you cannot supersede a superseded fact; assert a fresh
  one and link via `selma:supersedes` instead.

HTTP status mapping (for the wrapper):
- `BackendError` → 503
- `TransactionError` → 409
- `QueryError` → 400
- `OntologyError` → 422
- `ProvenanceError` / `SupersedeError` → 400
- Typed JSON error body in all cases.

---

## 6. Testing

Three layers:

### 6.1 Backend conformance suite

`tests/backends/conftest.py` parametrizes the `Backend` protocol tests across every
implementation (embedded now; the remote/managed stubs must pass the same suite before they
ship). This guarantees the three backends are genuinely interchangeable. Covers:
- Transactions (commit, rollback, isolation).
- Quad add/remove.
- SPARQL SELECT / ASK / CONSTRUCT / UPDATE.
- Named-graph provenance isolation.
- Crash recovery: restart the embedded store, assert durability.

### 6.2 Typed API tests

`tests/api/` exercises `remember`/`recall`/`find`/`relate`/`supersede`/`forget` against the
embedded backend, including:
- `as_of` time-travel queries.
- History inclusion (`include_history=True`).
- Soft vs hard delete semantics.
- Provenance required (`ProvenanceError` when `stated_by` missing).
- Supersede chain rejection (`SupersedeError`).
- Light entailment at query time (subclass / inverse / transitive).

### 6.3 Ontology + `/describe` tests

`tests/ontology/` asserts:
- The ontology is self-consistent: every class referenced in `superclasses` exists; every
  property's `domain`/`range` exists.
- `/describe` output is valid JSON-LD with no missing `description` fields.
- `example_queries` actually execute against an empty store without error.

### 6.4 Property-based tests (Hypothesis)

Generate random fact/supersede sequences to check temporal invariants never break: at any
`as_of` time, exactly one non-superseded `Fact` is visible per `(subject, predicate)` unless
multiple sources asserted independently (named graphs keep them distinct).

---

## 7. Decisions Log

| Decision | Choice | Alternatives considered |
|----------|--------|-------------------------|
| Foundation subsystem to design first | RDF/SPARQL memory core | Life-assistant core; autonomous execution; voice integration |
| Storage location | Pluggable; start with embedded in-process | Self-hosted triplestore; managed RDF cloud; (embedded chosen as starting default) |
| Client query model | Typed API + passthrough SPARQL, over a universal ontology that the store self-describes to clients | Raw SPARQL endpoint; typed API only |
| Ontology basis | Custom compact upper ontology | Adopt DOLCE/SUMO/BFO; custom core + public vocab links |
| Self-description format | JSON-LD + natural-language descriptions | SHACL/ShEx shapes; OpenAPI/GraphQL schema |
| Temporal & truth model | Timestamps + provenance/confidence | Timestamps only; latest-value only |
| Reasoning load | Light entailment rules at query time | Dumb store + smart clients; full OWL reasoner |
| Approach | Python library + embedded store (A) | Standalone microservice (B); rdflib-only (C) |

---

## 8. Sub-project Decomposition (context for later specs)

The Selma platform decomposes into at least four independent sub-projects, each with its own
spec → plan → implementation cycle. This spec covers the first.

1. **`selma.memory`** (this spec) — semantic RDF/SPARQL memory core.
2. **`selma.life`** — life-assistant core: reminders, scheduling, activity capture. Client
   of `selma.memory`.
3. **`selma.agents`** — autonomous task execution and project coordination. Client of
   `selma.memory`.
4. **`selma.voice`** — voice-assistant integration gateway (Alexa, Siri, Cortana, Google
   Home). Routes intents into `selma.memory` (and later into `selma.life`).

Each later sub-project consumes the typed API + `/describe` contract fixed here.