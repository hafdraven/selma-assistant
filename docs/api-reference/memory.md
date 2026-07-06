# `selma.memory` API reference

`selma.memory` is the semantic RDF/SPARQL memory core of the Selma platform.
Every piece of knowledge is stored as an RDF reified fact with provenance and
temporal metadata, and exposed through a typed Python API backed by an
embedded Oxigraph triplestore. It is the foundation that `selma.life`,
`selma.agents`, and `selma.voice` build on, and it depends on nothing else
inside Selma.

## Public exports

| Name | Kind | Description |
|------|------|-------------|
| `MemoryAPI` | class | Typed read/write surface over a `Backend`. |
| `Backend` | protocol | The storage contract every backend honors. |
| `EmbeddedOxigraph` | class | In-process pyoxigraph backend (default). |
| `get_backend` | function | Factory selecting a backend from a `BackendConfig`. |
| `BackendConfig` | dataclass | Backend selection configuration. |
| `describe` | function | Return the ontology self-description. |
| `MemoryError` | exception | Base class for all `selma.memory` errors. |
| `BackendError` | exception | Store unreachable / disk full / connection lost. |
| `TransactionError` | exception | Commit/rollback failed (concurrent write conflict). |
| `QueryError` | exception | Malformed SPARQL or unknown prefix. |
| `OntologyError` | exception | Unknown class/property or range/domain violation. |
| `ProvenanceError` | exception | `remember`/`supersede` called without `stated_by`. |
| `SupersedeError` | exception | Superseding a fact that is already superseded. |

## `MemoryAPI`

```python
MemoryAPI(backend) -> None
```

Wraps a `Backend` with a typed, provenance-required surface. `backend` is any
object honoring the `Backend` protocol (typically `EmbeddedOxigraph`).

### Methods

| Method | Signature | Returns | Raises |
|--------|-----------|---------|--------|
| `ask` | `ask(sparql_str: str, bindings: dict \| None = None)` | backend result | `QueryError` |
| `describe` | `describe()` | `OntologyDescription` | — |
| `remember` | `remember(subject, predicate, obj, *, stated_by, confidence=1.0, valid_from=None, valid_to=None, source=None)` | subject term | `ProvenanceError` |
| `relate` | `relate(subject, predicate, obj, *, stated_by, valid_from=None, valid_to=None)` | subject term | `ProvenanceError` |
| `recall` | `recall(subject=None, predicate=None, obj=None, *, as_of=None, include_history=False)` | `list[dict]` | — |
| `find` | `find(class_uri: str, *, filters=None, as_of=None)` | `list` | — |
| `supersede` | `supersede(fact_uri, new_value, *, stated_by, reason=None)` | new fact blank node | `ProvenanceError`, `SupersedeError` |
| `forget` | `forget(subject=None, predicate=None, obj=None, *, soft=True, reason=None)` | `int` | `QueryError`, `ProvenanceError` |

`ask` routes `INSERT`/`DELETE`/`LOAD`/`CLEAR`/`CREATE`/`DROP`/`COPY`/`MOVE`/`ADD`
verbs to `backend.update`; `SELECT`/`CONSTRUCT`/`ASK` to `backend.query`.

`remember` generates a blank-node reification node (`_:factNNN`) carrying
`rdf:subject`, `rdf:predicate`, `rdf:object` plus `selma:statedBy`,
`selma:recordedAt`, `selma:validFrom`, and optional `selma:confidence`,
`selma:validTo`, `selma:source`. If `subject` is `None` a fresh blank node is
generated and returned.

`forget` retires (soft) or physically removes (hard) reified facts matching
the `(subject, predicate, obj)` filter. Soft delete sets `validTo = now` on
the matching reification nodes; hard delete logs to the `selma:audit` named
graph then removes the quads. At least one of `subject`/`predicate`/`obj`
must be given. Hard delete (`soft=False`) requires a `reason`.

### Example

```python
from selma.memory import MemoryAPI, EmbeddedOxigraph
from pyoxigraph import NamedNode

mem = MemoryAPI(EmbeddedOxigraph())
SELF = NamedNode("https://selma.example/ns/core#self")

# Store a reified fact with provenance.
s = mem.remember(NamedNode("http://ex/alice"),
                 NamedNode("http://ex/knows"),
                 NamedNode("http://ex/bob"),
                 stated_by=SELF)

# Read current facts (history excluded by default).
rows = mem.recall(subject=NamedNode("http://ex/alice"))
for row in rows:
    print(row["p"], row["o"], row["vf"], row["vt"])

# Retire the old fact and assert a replacement.
mem.supersede(NamedNode("http://ex/alice"),
              NamedNode("http://ex/carol"),
              stated_by=SELF, reason="updated relationship")
```

## `Backend` (Protocol)

```python
@runtime_checkable
class Backend(Protocol):
    def begin(self) -> Txn: ...
    def commit(self, txn: Txn) -> None: ...
    def rollback(self, txn: Txn) -> None: ...
    def add(self, txn, s, p, o, ctx=None) -> None: ...
    def remove(self, txn, s, p, o, ctx=None) -> None: ...
    def query(self, sparql: str, *, bindings=None) -> QueryResult: ...
    def update(self, sparql: str, *, bindings=None) -> None: ...
    def count(self, s, p, o, ctx=None) -> int: ...
    def close(self) -> None: ...
```

The storage contract (spec §3). `Term` is `NamedNode | BlankNode | Literal`;
`GraphName` is `NamedNode | BlankNode | DefaultGraph`; `QueryResult` is
`QuerySolutions | QueryBoolean | QueryTriples`.

## `EmbeddedOxigraph`

```python
EmbeddedOxigraph(*, path: Path | str | None = None) -> None
```

In-process pyoxigraph store. `path=None` runs in RAM; a directory path
persists to disk. Honors the `Backend` protocol. Each `update()` is atomic
(pyoxigraph guarantee); `begin`/`commit`/`rollback` are no-ops because
pyoxigraph 0.5.9 does not expose explicit multi-call transactions.

| Method | Signature | Returns | Raises |
|--------|-----------|---------|--------|
| `begin` | `begin() -> Txn` | `None` | — |
| `commit` | `commit(txn) -> None` | — | — |
| `rollback` | `rollback(txn) -> None` | — | — |
| `add` | `add(txn, s, p, o, ctx=None) -> None` | — | `BackendError` |
| `remove` | `remove(txn, s, p, o, ctx=None) -> None` | — | `BackendError` |
| `query` | `query(sparql, *, bindings=None) -> QueryResult` | result set | `QueryError` |
| `update` | `update(sparql, *, bindings=None) -> None` | — | `QueryError` |
| `count` | `count(s, p, o, ctx=None) -> int` | count | `BackendError` |
| `close` | `close() -> None` | — | — |

### Example

```python
from selma.memory import EmbeddedOxigraph

store = EmbeddedOxigraph()               # in-RAM
store.update("INSERT DATA { <http://ex/a> <http://ex/p> <http://ex/b> }")
for row in store.query("SELECT ?s ?o WHERE { ?s ?p ?o }"):
    print(row["s"], row["o"])
print(store.count(None, None, None))     # 1
store.close()
```

## `BackendConfig`

```python
@dataclass
class BackendConfig:
    kind: str = "embedded"
    path: Path | str | None = None
```

Selects a backend via `get_backend(config)`. `kind="embedded"` picks
`EmbeddedOxigraph(path=path)`; `"remote"` and `"managed"` are stubbed for
future work.

## `describe()`

```python
describe() -> OntologyDescription
```

Returns the ontology self-description (the `/describe` payload). The
`OntologyDescription` dataclass exposes `context`, `classes`
(`list[OntologyClass]`), `properties` (`list[OntologyProperty]`),
`entailment_rules`, and `example_queries`, plus a `to_dict()` method.

## Exceptions

| Exception | When raised |
|-----------|-------------|
| `MemoryError` | Base class for all `selma.memory` errors. |
| `BackendError` | Store unreachable, disk full, or `add`/`remove`/`count` OS failure. |
| `TransactionError` | Commit/rollback failed (e.g. concurrent write conflict). |
| `QueryError` | Malformed SPARQL or unknown prefix; also by `forget` when no filter is given. Carries the offending query on `.query`. |
| `OntologyError` | Typed-API call references an unknown class/property or violates range/domain. |
| `ProvenanceError` | `remember`/`relate`/`supersede` called without `stated_by`, or hard `forget` without a `reason`. |
| `SupersedeError` | `supersede` target already has a `validTo` (already superseded). |

## Cross-references

- Architecture overview: [../architecture.md](../architecture.md)
- Getting started: [../getting-started.md](../getting-started.md)
- Life API reference: [life.md](life.md)
- Agents API reference: [agents.md](agents.md)
- Voice API reference: [voice.md](voice.md)
- Design spec: [../superpowers/specs/2026-07-05-selma-memory-core-design.md](../superpowers/specs/2026-07-05-selma-memory-core-design.md)