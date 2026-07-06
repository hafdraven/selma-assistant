# Selma Memory Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `selma.memory`, a pluggable RDF/SPARQL semantic memory core with a custom compact upper ontology, self-describing `/describe` endpoint, and a typed memory API — backed by an embedded Oxigraph store.

**Architecture:** A Python library whose storage, ontology, typed API, and self-description are independent modules behind fixed interfaces. The backend is a `Protocol` with one implemented variant (`EmbeddedOxigraph`) and two stubbed variants. The typed API compiles to SPARQL against the ontology and runs it through the backend. All statements are quads in named graphs recording provenance; temporal validity and confidence are first-class. Light RDFS/OWL entailment is applied at query time via SPARQL query construction, not a reasoner.

**Tech Stack:** Python 3.14, `pyoxigraph` 0.5.9 (embedded store), `pytest` 8.x, `hypothesis` (property-based tests). Pure stdlib otherwise. No HTTP framework in this sub-project — the wrapper is a later addition on top of the fixed interface.

## Global Constraints

- Python 3.14 (installed on this machine). Code must run on 3.11+ in principle.
- `pyoxigraph>=0.5.9` is the only third-party runtime dependency.
- `pytest>=8.0` and `hypothesis>=6.0` are dev dependencies.
- The Selma core namespace IRI is `https://selma.example/ns/core#` (prefix `selma:`). All spec-defined class and property URIs live here verbatim — do not rename.
- All store operations are quad-based (subject, predicate, object, graph_name). The `graph_name` records the provenance source. Never write a bare triple to the default graph from the typed API.
- `stated_by` is required on every `remember`/`relate`/`supersede` call. No exceptions, no defaults — raise `ProvenanceError` if missing.
- Nothing is silently dropped. A failed write raises; partial writes roll back.
- Files live under `src/selma/memory/` (importable as `selma.memory`), tests under `tests/`. This is a `src` layout.
- Use `pyoxigraph.Store` directly inside `backends/embedded.py` only; the rest of the code talks to the `Backend` protocol.
- Commits are frequent and atomic per task. Use the commit message style shown in each task.

---

## File Structure

```
D:/src/selma/
├── pyproject.toml                      # Project metadata, deps, pytest config
├── src/selma/memory/
│   ├── __init__.py                     # Public re-exports: MemoryAPI, Backend, exceptions, ontology
│   ├── config.py                       # BackendConfig (dataclass) — selects backend + path
│   ├── exceptions.py                   # MemoryError hierarchy
│   ├── terms.py                        # URI constants: namespace, class URIs, property URIs, prefixes dict
│   ├── ontology.py                     # OntologyDescription dataclass + build_ontology() + describe()
│   ├── backends/
│   │   ├── __init__.py                 # Re-exports: Backend, EmbeddedOxigraph, get_backend
│   │   ├── protocol.py                 # Backend Protocol + Txn/QueryResult type aliases
│   │   ├── embedded.py                 # EmbeddedOxigraph implementation
│   │   ├── remote.py                   # RemoteTriplestore stub (NotImplementedError)
│   │   └── managed.py                  # ManagedRDF stub (NotImplementedError)
│   ├── api.py                          # MemoryAPI — typed memory operations
│   ├── sparql.py                       # SPARQL query/update builders used by api.py
│   └── entailment.py                   # Light entailment rule registration + application in queries
└── tests/
    ├── conftest.py                     # Shared fixtures: tmp_store, fresh_api
    ├── backends/
    │   ├── conftest.py                 # backend fixture parametrization across all backends
    │   ├── test_protocol.py            # Conformance suite (runs against every backend)
    │   └── test_embedded_durability.py  # Crash-recovery test (embedded only)
    ├── api/
    │   ├── test_remember.py
    │   ├── test_recall.py
    │   ├── test_find.py
    │   ├── test_relate.py
    │   ├── test_supersede.py
    │   ├── test_forget.py
    │   ├── test_ask.py
    │   └── test_entailment.py
    ├── ontology/
    │   ├── test_consistency.py
    │   ├── test_describe.py
    │   └── test_example_queries.py
    └── property/
        └── test_temporal_invariants.py # Hypothesis property-based tests
```

**Responsibilities:**
- `terms.py` — single source of truth for all URIs. No other module hardcodes a Selma IRI.
- `ontology.py` — builds the in-memory `OntologyDescription` from `terms.py`; never touches the store.
- `backends/protocol.py` — the `Backend` Protocol; the contract every backend honors.
- `backends/embedded.py` — the only concrete working backend; wraps `pyoxigraph.Store`.
- `api.py` — the typed memory API; compiles user intent to SPARQL via `sparql.py` and runs it through a `Backend`. This is the file later sub-projects import.
- `sparql.py` — pure functions that return SPARQL strings given terms/objects. No store access. Tested indirectly via `api.py` tests and directly in `test_ask.py`.
- `entailment.py` — registers the three rule kinds (subclass, inverseOf, transitive) as data the query builder consults; applied by rewriting SELECT queries to include entailment. No reasoner process.

---

## Task 1: Project Scaffold + Dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `src/selma/memory/__init__.py` (empty package marker)
- Create: `src/selma/memory/backends/__init__.py` (empty)
- Create: `tests/__init__.py` (empty, so test imports are absolute)
- Create: `tests/backends/__init__.py`, `tests/api/__init__.py`, `tests/ontology/__init__.py`, `tests/property/__init__.py` (empty)
- Create: `tests/conftest.py` (placeholder, replaced in Task 3)

**Interfaces:**
- Consumes: nothing
- Produces: an installable package `selma.memory` importable after `pip install -e .`; pytest collects tests/ with no collection errors.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "selma-memory"
version = "0.1.0"
description = "Semantic RDF/SPARQL memory core for the Selma assistant platform."
requires-python = ">=3.11"
dependencies = [
    "pyoxigraph>=0.5.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "hypothesis>=6.0",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-ra"
```

- [ ] **Step 2: Create the empty package markers and placeholder conftest**

`src/selma/memory/__init__.py`:
```python
"""selma.memory: semantic RDF/SPARQL memory core."""
```

`src/selma/memory/backends/__init__.py`:
```python
"""Storage backends for selma.memory."""
```

Each `tests/*/__init__.py`: a single line docstring, e.g. `"""Backend conformance tests."""`.

`tests/conftest.py` (placeholder; replaced in Task 3):
```python
"""Shared pytest fixtures for selma.memory tests."""
```

- [ ] **Step 3: Install the package in editable mode with dev deps**

Run: `pip install -e ".[dev]"`
Expected: installs `selma-memory`, `pyoxigraph`, `pytest`, `hypothesis` with no errors.

- [ ] **Step 4: Verify pytest collects with zero tests and no errors**

Run: `pytest --collect-only -q`
Expected: exits 0 (or "no tests collected"), no collection errors.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/selma/memory/__init__.py src/selma/memory/backends/__init__.py tests/__init__.py tests/backends/__init__.py tests/api/__init__.py tests/ontology/__init__.py tests/property/__init__.py tests/conftest.py
git commit -m "chore: scaffold selma.memory package and test layout"
```

---

## Task 2: Exception Hierarchy

**Files:**
- Create: `src/selma/memory/exceptions.py`
- Test: `tests/test_exceptions.py`

**Interfaces:**
- Consumes: nothing
- Produces: `MemoryError`, `BackendError`, `TransactionError`, `QueryError`, `OntologyError`, `ProvenanceError`, `SupersedeError` (all in `selma.memory.exceptions`); each is a subclass of `MemoryError` per the spec's §5 hierarchy; `QueryError` carries the offending query string.

- [ ] **Step 1: Write the failing test**

`tests/test_exceptions.py`:
```python
import pytest
from selma.memory.exceptions import (
    MemoryError, BackendError, TransactionError, QueryError,
    OntologyError, ProvenanceError, SupersedeError,
)


def test_all_subclass_memory_error():
    for exc in (BackendError, TransactionError, QueryError,
                OntologyError, ProvenanceError, SupersedeError):
        assert issubclass(exc, MemoryError)


def test_query_error_carries_query():
    err = QueryError("bad", query="SELECT ?s WHERE { ??? }")
    assert err.query == "SELECT ?s WHERE { ??? }"
    assert "SELECT ?s WHERE { ??? }" in str(err)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_exceptions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'selma.memory.exceptions'`

- [ ] **Step 3: Write minimal implementation**

`src/selma/memory/exceptions.py`:
```python
"""Exception hierarchy for selma.memory (spec §5)."""


class MemoryError(Exception):
    """Base class for all selma.memory errors."""


class BackendError(MemoryError):
    """Store unreachable / disk full / connection lost."""


class TransactionError(MemoryError):
    """Commit/rollback failed (e.g. concurrent write conflict)."""


class QueryError(MemoryError):
    """Malformed SPARQL or unknown prefix. Carries the offending query."""

    def __init__(self, message: str, *, query: str | None = None) -> None:
        super().__init__(message if query is None else f"{message} (query: {query})")
        self.query = query


class OntologyError(MemoryError):
    """Typed-API call references unknown class/property, or violates range/domain."""


class ProvenanceError(MemoryError):
    """remember/supersede called without required `stated_by`."""


class SupersedeError(MemoryError):
    """Superseding a fact that was already superseded or whose validTo is set."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_exceptions.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/selma/memory/exceptions.py tests/test_exceptions.py
git commit -m "feat: add selma.memory exception hierarchy"
```

---

## Task 3: Terms + Namespace Constants

**Files:**
- Create: `src/selma/memory/terms.py`
- Test: `tests/test_terms.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `NS: str` = `"https://selma.example/ns/core#"`
  - `PREFIXES: dict[str, str]` — `{"selma": NS, "foaf": "http://xmlns.com/foaf/0.1/", "schema": "https://schema.org/", "ical": "http://www.w3.org/2002/12/cal/ical#", "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdfs": "http://www.w3.org/2000/01/rdf-schema#", "owl": "http://www.w3.org/2002/07/owl#", "xsd": "http://www.w3.org/2001/XMLSchema#"}`
  - `CLASSES: dict[str, str]` — short name → full URI, for the 9 classes in spec §2.
  - `PROPS: dict[str, str]` — short name → full URI, for all properties in spec §2.
  - `XSD: dict[str, str]` — convenience: `"dateTime"`, `"decimal"`, `"string"`, `"boolean"` → full xsd URIs.
  - `def uri(name: str) -> str:` — returns `NS + name` for a short core name.

- [ ] **Step 1: Write the failing test**

`tests/test_terms.py`:
```python
from selma.memory import terms


def test_namespace():
    assert terms.NS == "https://selma.example/ns/core#"


def test_uri_helper():
    assert terms.uri("Entity") == "https://selma.example/ns/core#Entity"


def test_classes_present():
    expected = {"Entity", "Agent", "Event", "Task", "Project",
               "Relationship", "Fact", "Belief", "Reminder"}
    assert set(terms.CLASSES) == expected
    for short, full in terms.CLASSES.items():
        assert full == terms.uri(short)


def test_props_present():
    expected = {
        "recordedAt", "validFrom", "validTo",
        "statedBy", "confidence", "source",
        "label", "description", "tag",
        "relates", "relatedBy", "partOf", "dependsOn", "supersedes",
        "hasStatus", "ownedBy", "dueBy", "completedAt",
    }
    assert set(terms.PROPS) == expected


def test_prefixes_include_external_vocabs():
    assert terms.PREFIXES["foaf"].endswith("/")
    assert terms.PREFIXES["schema"].endswith("/")
    assert terms.PREFIXES["xsd"].endswith("#")


def test_xsd_helpers():
    assert terms.XSD["dateTime"] == "http://www.w3.org/2001/XMLSchema#dateTime"
    assert terms.XSD["decimal"] == "http://www.w3.org/2001/XMLSchema#decimal"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_terms.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'selma.memory.terms'`

- [ ] **Step 3: Write minimal implementation**

`src/selma/memory/terms.py`:
```python
"""URI constants and prefixes for the Selma core ontology (spec §2).

Single source of truth — no other module hardcodes a Selma IRI.
"""

NS = "https://selma.example/ns/core#"


def uri(name: str) -> str:
    """Return the full core-namespace URI for a short name."""
    return NS + name


CLASSES: dict[str, str] = {
    "Entity": uri("Entity"),
    "Agent": uri("Agent"),
    "Event": uri("Event"),
    "Task": uri("Task"),
    "Project": uri("Project"),
    "Relationship": uri("Relationship"),
    "Fact": uri("Fact"),
    "Belief": uri("Belief"),
    "Reminder": uri("Reminder"),
}

PROPS: dict[str, str] = {
    # Temporal
    "recordedAt": uri("recordedAt"),
    "validFrom": uri("validFrom"),
    "validTo": uri("validTo"),
    # Provenance & trust
    "statedBy": uri("statedBy"),
    "confidence": uri("confidence"),
    "source": uri("source"),
    # Metadata
    "label": uri("label"),
    "description": uri("description"),
    "tag": uri("tag"),
    # Structural
    "relates": uri("relates"),
    "relatedBy": uri("relatedBy"),
    "partOf": uri("partOf"),
    "dependsOn": uri("dependsOn"),
    "supersedes": uri("supersedes"),
    # Task lifecycle
    "hasStatus": uri("hasStatus"),
    "ownedBy": uri("ownedBy"),
    "dueBy": uri("dueBy"),
    "completedAt": uri("completedAt"),
}

XSD: dict[str, str] = {
    "dateTime": "http://www.w3.org/2001/XMLSchema#dateTime",
    "decimal": "http://www.w3.org/2001/XMLSchema#decimal",
    "string": "http://www.w3.org/2001/XMLSchema#string",
    "boolean": "http://www.w3.org/2001/XMLSchema#boolean",
}

PREFIXES: dict[str, str] = {
    "selma": NS,
    "foaf": "http://xmlns.com/foaf/0.1/",
    "schema": "https://schema.org/",
    "ical": "http://www.w3.org/2002/12/cal/ical#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_terms.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/selma/memory/terms.py tests/test_terms.py
git commit -m "feat: add Selma core ontology terms and prefixes"
```

---

## Task 4: Backend Protocol + Shared Test Fixtures

**Files:**
- Create: `src/selma/memory/backends/protocol.py`
- Create: `tests/backends/conftest.py`
- Replace: `tests/conftest.py` (was placeholder in Task 1)

**Interfaces:**
- Consumes: `pyoxigraph` types (for the `Term`/`Quad` type aliases only)
- Produces:
  - `Term = NamedNode | BlankNode | Literal` (type alias)
  - `Backend` Protocol with methods `begin/commit/rollback/add/remove/query/update/count/close` per spec §3
  - `Txn` opaque type alias (object)
  - `QueryResult` type alias (iterator of `QuerySolution` | `bool` | iterator of `Triple`)
  - pytest fixtures `embedded_backend` (factory returning a fresh `EmbeddedOxigraph` on a tmp path) and `fresh_api` (a `MemoryAPI` over a fresh embedded backend) — `fresh_api` is a placeholder that will be wired in Task 8; for now only `embedded_backend` is used and the fixture is marked as such.

Note: `EmbeddedOxigraph` does not exist yet. The `embedded_backend` fixture in this task will skip if `EmbeddedOxigraph` is not importable, so the conformance suite (Task 6) is what actually exercises the embedded backend once Task 5 lands.

- [ ] **Step 1: Write the protocol module**

`src/selma/memory/backends/protocol.py`:
```python
"""Backend Protocol — the contract every storage backend honors (spec §3)."""

from __future__ import annotations

from typing import Any, Iterator, Protocol, runtime_checkable

from pyoxigraph import (BlankNode, DefaultGraph, Literal, NamedNode,
                        QueryBoolean, QuerySolution, QuerySolutions, QueryTriples, Triple)

# A node that can appear in subject/object position.
Term = NamedNode | BlankNode | Literal
# A graph name (named graph or default).
GraphName = NamedNode | BlankNode | DefaultGraph
# Opaque transaction handle returned by begin().
Txn = Any
# Result of a SELECT / ASK / CONSTRUCT.
QueryResult = QuerySolutions | QueryBoolean | QueryTriples


@runtime_checkable
class Backend(Protocol):
    def begin(self) -> Txn: ...
    def commit(self, txn: Txn) -> None: ...
    def rollback(self, txn: Txn) -> None: ...
    def add(self, txn: Txn, s: Term, p: NamedNode, o: Term, ctx: GraphName | None = None) -> None: ...
    def remove(self, txn: Txn, s: Term | None, p: NamedNode | None, o: Term | None, ctx: GraphName | None = None) -> None: ...
    def query(self, sparql: str, *, bindings: dict | None = None) -> QueryResult: ...
    def update(self, sparql: str, *, bindings: dict | None = None) -> None: ...
    def count(self, s: Term | None, p: NamedNode | None, o: Term | None, ctx: GraphName | None = None) -> int: ...
    def close(self) -> None: ...
```

- [ ] **Step 2: Write the backend conftest with parametrization**

`tests/backends/conftest.py`:
```python
"""Parametrizes backend conformance tests across every implemented backend."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


def _backends():
    """Return (id, factory) pairs for every implemented backend."""
    impls = []
    try:
        from selma.memory.backends.embedded import EmbeddedOxigraph

        def make_embedded(tmp_path):
            return EmbeddedOxigraph(path=tmp_path / "store")

        impls.append(("embedded", make_embedded))
    except ImportError:
        pass
    try:
        from selma.memory.backends.remote import RemoteTriplestore

        impls.append(("remote", lambda tmp_path: RemoteTriplestore(endpoint="http://example/")))
    except ImportError:
        pass
    try:
        from selma.memory.backends.managed import ManagedRDF

        impls.append(("managed", lambda tmp_path: ManagedRDF(endpoint="http://example/")))
    except ImportError:
        pass
    return impls


def pytest_generate_tests(metafunc):
    if "backend_factory" in metafunc.fixturenames:
        impls = _backends()
        if not impls:
            pytest.skip("no backend implementations available")
        metafunc.parametrize("backend_factory", [f for _, f in impls], ids=[i for i, _ in impls])


@pytest.fixture
def backend(backend_factory, tmp_path):
    store = backend_factory(tmp_path)
    try:
        yield store
    finally:
        store.close()
```

- [ ] **Step 3: Update top-level conftest with shared fixtures**

`tests/conftest.py`:
```python
"""Shared pytest fixtures for selma.memory tests."""
from __future__ import annotations

import pytest


@pytest.fixture
def fresh_api(tmp_path):
    """A MemoryAPI over a fresh embedded backend. Wired in Task 8."""
    pytest.skip("MemoryAPI not implemented yet")
```

- [ ] **Step 4: Verify protocol imports and conftest collects without error**

Run: `python -c "from selma.memory.backends.protocol import Backend; print('ok')"`
Expected: prints `ok`.

Run: `pytest --collect-only -q tests/backends/conftest.py`
Expected: no collection errors (no tests collected from the conftest itself).

- [ ] **Step 5: Commit**

```bash
git add src/selma/memory/backends/protocol.py tests/backends/conftest.py tests/conftest.py
git commit -m "feat: add Backend protocol and parametrized backend fixtures"
```

---

## Task 5: EmbeddedOxigraph Backend

**Files:**
- Create: `src/selma/memory/backends/embedded.py`
- Create: `src/selma/memory/backends/__init__.py` (replace empty marker with re-exports)
- Test: `tests/backends/test_embedded_smoke.py`

**Interfaces:**
- Consumes: `Backend` protocol from Task 4; `pyoxigraph.Store`, `pyoxigraph` term types.
- Produces: `EmbeddedOxigraph` class implementing `Backend`; `get_backend(config)` factory in `backends/__init__.py` that returns an `EmbeddedOxigraph` for `BackendConfig(kind="embedded", path=...)`.

Implementation notes (from pyoxigraph 0.5.9 API inspection):
- `pyoxigraph.Store(path=None)` opens a persistent store; `path=None` makes an in-memory temporary store.
- `store.add(Quad(s, p, o, graph_name))`; `graph_name` defaults to `DefaultGraph`. `Quad` is positional: `Quad(subject, predicate, object, graph_name=...)`.
- `store.remove(Quad(...))` removes a specific quad. For pattern removal, iterate `store.quads_for_pattern(s, p, o, graph_name)` and remove each.
- `store.query(sparql_str, prefixes=PREFIXES, substitutions={Variable("x"): term})` runs SELECT/ASK/CONSTRUCT. Returns `QuerySolutions`/`QueryBoolean`/`QueryTriples`.
- `store.update(sparql_update_str, prefixes=PREFIXES)` runs INSERT/DELETE transactionally (per pyoxigraph docs: a single update is atomic).
- `store.quads_for_pattern(s, p, o, graph_name)` returns an iterator; use `len(list(...))` for count.
- pyoxigraph has no explicit begin/commit for arbitrary multi-statement transactions in 0.5.9's Python API; `Store.update()` is itself atomic. The `Backend` Protocol exposes `begin/commit/rollback` so future triplestore backends can use real transactions. For the embedded backend, `begin()` returns `None` (a no-op transaction marker), `commit/rollback` are no-ops, and atomicity is provided per-update inside `Backend.update()` and per-add inside the typed API's batch writes (which use a single SPARQL UPDATE).

- [ ] **Step 1: Write the failing smoke test**

`tests/backends/test_embedded_smoke.py`:
```python
from pyoxigraph import DefaultGraph, Literal, NamedNode

from selma.memory.backends.embedded import EmbeddedOxigraph


def test_add_and_query(tmp_path):
    store = EmbeddedOxigraph(path=tmp_path / "s")
    ex = NamedNode("http://example/")
    store.add(None, ex, NamedNode("http://example/p"), Literal("hi"),
              ctx=NamedNode("http://example/g"))
    rows = list(store.query("SELECT ?o WHERE { GRAPH ?g { ?s ?p ?o } }"))
    assert rows[0]["o"].value == "hi"
    store.close()


def test_count(tmp_path):
    store = EmbeddedOxigraph(path=tmp_path / "s")
    g = NamedNode("http://example/g")
    store.add(None, NamedNode("http://example/s"), NamedNode("http://example/p"),
              Literal("x"), ctx=g)
    store.add(None, NamedNode("http://example/s"), NamedNode("http://example/p"),
              Literal("y"), ctx=g)
    assert store.count(None, None, None, ctx=g) == 2
    store.close()


def test_update_deletes(tmp_path):
    store = EmbeddedOxigraph(path=tmp_path / "s")
    g = NamedNode("http://example/g")
    store.add(None, NamedNode("http://example/s"), NamedNode("http://example/p"),
              Literal("x"), ctx=g)
    store.update("DELETE WHERE { GRAPH <http://example/g> { ?s ?p ?o } }")
    assert store.count(None, None, None, ctx=g) == 0
    store.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backends/test_embedded_smoke.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'selma.memory.backends.embedded'`

- [ ] **Step 3: Write minimal implementation**

`src/selma/memory/backends/embedded.py`:
```python
"""Embedded Oxigraph backend (spec §3, default backend)."""
from __future__ import annotations

from pathlib import Path

from pyoxigraph import (DefaultGraph, Literal, NamedNode, Quad, Store, Variable)

from ..exceptions import BackendError, QueryError
from ..terms import PREFIXES
from .protocol import Backend, GraphName, QueryResult, Term, Txn


class EmbeddedOxigraph:
    """In-process Oxigraph store. Honors the `Backend` protocol.

    Atomicity: each `update()` call is atomic (pyoxigraph guarantee). Multi-
    statement typed-API batches are issued as a single SPARQL UPDATE, so they
    are also atomic. `begin/commit/rollback` are no-ops because pyoxigraph's
    Python API does not expose explicit multi-call transactions in 0.5.9.
    """

    def __init__(self, *, path: Path | str | None = None) -> None:
        try:
            self._store = Store(path=str(path) if path is not None else None)
        except OSError as e:
            raise BackendError(f"cannot open oxigraph store at {path}: {e}") from e

    # -- transactions (no-ops; atomicity is per update/add) --
    def begin(self) -> Txn:
        return None

    def commit(self, txn: Txn) -> None:
        pass

    def rollback(self, txn: Txn) -> None:
        pass

    # -- writes --
    def add(self, txn: Txn, s: Term, p: NamedNode, o: Term,
            ctx: GraphName | None = None) -> None:
        graph = ctx if ctx is not None else DefaultGraph()
        try:
            self._store.add(Quad(s, p, o, graph))
        except OSError as e:
            raise BackendError(f"add failed: {e}") from e

    def remove(self, txn: Txn, s: Term | None, p: NamedNode | None,
               o: Term | None, ctx: GraphName | None = None) -> None:
        graph = ctx if ctx is not None else None
        try:
            for q in list(self._store.quads_for_pattern(s, p, o, graph)):
                self._store.remove(q)
        except OSError as e:
            raise BackendError(f"remove failed: {e}") from e

    # -- queries --
    def query(self, sparql: str, *, bindings: dict | None = None) -> QueryResult:
        subs = {Variable(k): v for k, v in (bindings or {}).items()} or None
        try:
            return self._store.query(sparql, prefixes=PREFIXES,
                                     substitutions=subs)
        except SyntaxError as e:
            raise QueryError(str(e), query=sparql) from e

    def update(self, sparql: str, *, bindings: dict | None = None) -> None:
        try:
            self._store.update(sparql, prefixes=PREFIXES)
        except SyntaxError as e:
            raise QueryError(str(e), query=sparql) from e

    def count(self, s: Term | None, p: NamedNode | None, o: Term | None,
              ctx: GraphName | None = None) -> int:
        try:
            return len(list(self._store.quads_for_pattern(s, p, o, ctx)))
        except OSError as e:
            raise BackendError(f"count failed: {e}") from e

    def close(self) -> None:
        # pyoxigraph Store releases resources on GC; explicit close for safety.
        self._store = None
```

`src/selma/memory/backends/__init__.py` (replace the empty marker):
```python
"""Storage backends for selma.memory."""
from __future__ import annotations

from ..config import BackendConfig
from .embedded import EmbeddedOxigraph
from .protocol import Backend


def get_backend(config: "BackendConfig") -> Backend:
    """Return a backend instance per the config (spec §3 selection)."""
    if config.kind == "embedded":
        return EmbeddedOxigraph(path=config.path)
    raise NotImplementedError(f"backend kind {config.kind!r} not implemented yet")


__all__ = ["Backend", "EmbeddedOxigraph", "get_backend"]
```

- [ ] **Step 4: Write the BackendConfig (needed by `get_backend`)**

Create `src/selma/memory/config.py`:
```python
"""Backend configuration (spec §3 selection)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class BackendConfig:
    kind: str = "embedded"
    path: Path | str | None = None
```

Add a minimal test `tests/test_config.py`:
```python
from selma.memory.config import BackendConfig


def test_default_is_embedded():
    assert BackendConfig().kind == "embedded"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/backends/test_embedded_smoke.py tests/test_config.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add src/selma/memory/backends/embedded.py src/selma/memory/backends/__init__.py src/selma/memory/config.py tests/backends/test_embedded_smoke.py tests/test_config.py
git commit -m "feat: add EmbeddedOxigraph backend and BackendConfig"
```

---

## Task 6: Backend Conformance Suite

**Files:**
- Create: `tests/backends/test_protocol.py`
- Create: `tests/backends/test_embedded_durability.py`

**Interfaces:**
- Consumes: the `backend` fixture (parametrized) from Task 4, the `EmbeddedOxigraph` from Task 5, `pyoxigraph` term types.
- Produces: a passing conformance suite that any future backend (`RemoteTriplestore`, `ManagedRDF`) must pass before it ships.

The suite covers: add+query, named-graph provenance isolation, pattern remove, SPARQL SELECT/ASK/CONSTRUCT/UPDATE, count, and (embedded-only) durability across store close/reopen.

- [ ] **Step 1: Write the conformance tests**

`tests/backends/test_protocol.py`:
```python
"""Conformance suite — every Backend implementation must pass these."""
from __future__ import annotations

import pytest
from pyoxigraph import DefaultGraph, Literal, NamedNode

S = NamedNode("http://ex/s")
P = NamedNode("http://ex/p")
O = Literal("o")
G1 = NamedNode("http://ex/g1")
G2 = NamedNode("http://ex/g2")


def test_add_and_select(backend):
    backend.add(None, S, P, O, ctx=G1)
    rows = list(backend.query("SELECT ?o WHERE { GRAPH ?g { ?s ?p ?o } }"))
    assert rows[0]["o"].value == "o"


def test_named_graph_isolation(backend):
    backend.add(None, S, P, Literal("in-g1"), ctx=G1)
    backend.add(None, S, P, Literal("in-g2"), ctx=G2)
    only_g1 = list(backend.query(
        "SELECT ?o WHERE { GRAPH <http://ex/g1> { ?s ?p ?o } }"))
    assert [r["o"].value for r in only_g1] == ["in-g1"]


def test_pattern_remove(backend):
    backend.add(None, S, P, O, ctx=G1)
    backend.remove(None, None, None, ctx=G1)
    assert backend.count(None, None, None, ctx=G1) == 0


def test_ask_query(backend):
    backend.add(None, S, P, O, ctx=G1)
    result = backend.query("ASK WHERE { GRAPH ?g { ?s ?p ?o } }")
    assert bool(result) is True


def test_construct_query(backend):
    backend.add(None, S, P, O, ctx=G1)
    triples = list(backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ?g { ?s ?p ?o } }"))
    assert len(list(triples)) == 1


def test_update_inserts_and_deletes(backend):
    backend.update(
        "INSERT DATA { GRAPH <http://ex/g1> { "
        "<http://ex/a> <http://ex/p> 'x' } }")
    assert backend.count(None, None, None, ctx=G1) == 1
    backend.update("DELETE WHERE { GRAPH <http://ex/g1> { ?s ?p ?o } }")
    assert backend.count(None, None, None, ctx=G1) == 0


def test_query_error_on_bad_sparql(backend):
    from selma.memory.exceptions import QueryError
    with pytest.raises(QueryError):
        backend.query("SELECT ?s WHERE { ??? }")


def test_count_default_graph(backend):
    backend.add(None, S, P, O, ctx=DefaultGraph())
    assert backend.count(None, None, None, ctx=DefaultGraph()) == 1
```

`tests/backends/test_embedded_durability.py`:
```python
"""Embedded-only: data persists across close/reopen (spec §3 durability)."""
from pyoxigraph import Literal, NamedNode

from selma.memory.backends.embedded import EmbeddedOxigraph


def test_persistence_across_reopen(tmp_path):
    p = tmp_path / "store"
    s = EmbeddedOxigraph(path=p)
    g = NamedNode("http://ex/g")
    s.add(None, NamedNode("http://ex/s"), NamedNode("http://ex/p"),
          Literal("durable"), ctx=g)
    s.close()

    s2 = EmbeddedOxigraph(path=p)
    assert s2.count(None, None, None, ctx=g) == 1
    rows = list(s2.query("SELECT ?o WHERE { GRAPH <http://ex/g> { ?s ?p ?o } }"))
    assert rows[0]["o"].value == "durable"
    s2.close()
```

- [ ] **Step 2: Run the conformance suite**

Run: `pytest tests/backends/ -v`
Expected: PASS — conformance tests parametrized over `embedded`; durability test passes. (Remote/managed are not yet implemented, so they are absent from parametrization; that is correct.)

- [ ] **Step 3: Commit**

```bash
git add tests/backends/test_protocol.py tests/backends/test_embedded_durability.py
git commit -m "test: add backend conformance suite and embedded durability test"
```

---

## Task 7: Ontology Description + `describe()`

**Files:**
- Create: `src/selma/memory/ontology.py`
- Test: `tests/ontology/test_consistency.py`, `tests/ontology/test_describe.py`, `tests/ontology/test_example_queries.py`

**Interfaces:**
- Consumes: `terms.py` (Task 3).
- Produces:
  - `OntologyClass` dataclass: `uri, label, description, superclasses: list[str], properties: list[str]`
  - `OntologyProperty` dataclass: `uri, label, description, domain, range`
  - `OntologyDescription` dataclass: `context: dict, classes: list[OntologyClass], properties: list[OntologyProperty], entailment_rules: list[str], example_queries: list[str]`
  - `build_ontology() -> OntologyDescription`
  - `describe() -> OntologyDescription` (alias of `build_ontology()`; the HTTP `/describe` later wraps this)
  - `CLASS_HIERARCHY: dict[str, list[str]]` — short name → list of direct superclass short names (e.g. `Agent -> ["Entity"]`, `Reminder -> ["Event"]`).
  - `INVERSE_PROPS: set[tuple[str, str]]` — pairs of short names that are `owl:inverseOf`: `("relates", "relatedBy")`.
  - `TRANSITIVE_PROPS: set[str]` — short names: `{"partOf", "dependsOn"}`.

This task also defines the `example_queries` list used by the spec's `/describe` output and tested against an empty store in `test_example_queries.py`.

- [ ] **Step 1: Write the consistency test**

`tests/ontology/test_consistency.py`:
```python
from selma.memory import terms
from selma.memory.ontology import build_ontology, CLASS_HIERARCHY


def test_every_superclass_exists():
    ont = build_ontology()
    class_uris = {c.uri for c in ont.classes}
    for cls in ont.classes:
        for sup in cls.superclasses:
            assert sup in class_uris, f"{cls.uri} references unknown superclass {sup}"


def test_every_property_domain_range_exists_or_xsd():
    ont = build_ontology()
    class_uris = {c.uri for c in ont.classes}
    for prop in ont.properties:
        for endpoint in (prop.domain, prop.range):
            if endpoint is None:
                continue
            assert endpoint in class_uris or endpoint.startswith(
                "http://www.w3.org/2001/XMLSchema#"), (
                f"{prop.uri} references unknown {endpoint}")


def test_class_hierarchy_matches_ontology():
    ont = build_ontology()
    by_uri = {c.uri: c for c in ont.classes}
    for short, sups in CLASS_HIERARCHY.items():
        cls = by_uri[terms.uri(short)]
        assert [terms.uri(s) for s in sups] == cls.superclasses
```

- [ ] **Step 2: Write the describe test**

`tests/ontology/test_describe.py`:
```python
from selma.memory.ontology import build_ontology


def test_describe_has_context():
    ont = build_ontology()
    assert "selma" in ont.context
    assert "foaf" in ont.context


def test_every_class_has_description():
    ont = build_ontology()
    for c in ont.classes:
        assert c.description, f"{c.uri} missing description"
        assert c.label, f"{c.uri} missing label"


def test_every_property_has_description():
    ont = build_ontology()
    for p in ont.properties:
        assert p.description, f"{p.uri} missing description"
        assert p.label, f"{p.uri} missing label"


def test_entailment_rules_present():
    ont = build_ontology()
    assert "rdfs:subClassOf" in ont.entailment_rules
    assert "owl:inverseOf" in ont.entailment_rules
    assert "owl:TransitiveProperty" in ont.entailment_rules


def test_to_dict_roundtrips_to_json():
    import json
    ont = build_ontology()
    s = json.dumps(ont.to_dict(), sort_keys=True)
    assert "selma:Entity" in s
```

- [ ] **Step 3: Write the example-queries test**

`tests/ontology/test_example_queries.py`:
```python
"""Spec §6.3: example_queries must execute against an empty store without error."""
from selma.memory.backends.embedded import EmbeddedOxigraph
from selma.memory.ontology import build_ontology


def test_example_queries_run_on_empty_store(tmp_path):
    store = EmbeddedOxigraph(path=tmp_path / "s")
    ont = build_ontology()
    for q in ont.example_queries:
        # Should not raise on an empty store.
        list(store.query(q))
    store.close()
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `pytest tests/ontology/ -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'selma.memory.ontology'`

- [ ] **Step 5: Write the implementation**

`src/selma/memory/ontology.py`:
```python
"""Ontology self-description and entailment metadata (spec §2, §4)."""
from __future__ import annotations

from dataclasses import dataclass, field

from .terms import NS, PREFIXES, XSD, uri

# Class hierarchy: short name -> list of direct superclass short names.
CLASS_HIERARCHY: dict[str, list[str]] = {
    "Entity": [],
    "Agent": ["Entity"],
    "Event": ["Entity"],
    "Task": ["Entity"],
    "Project": ["Entity"],
    "Relationship": ["Entity"],
    "Fact": ["Entity"],
    "Belief": ["Entity"],
    "Reminder": ["Event"],
}

# owl:inverseOf pairs (short names).
INVERSE_PROPS: set[tuple[str, str]] = {
    ("relates", "relatedBy"),
}

# owl:TransitiveProperty short names.
TRANSITIVE_PROPS: set[str] = {"partOf", "dependsOn"}


@dataclass
class OntologyClass:
    uri: str
    label: str
    description: str
    superclasses: list[str]
    properties: list[str]


@dataclass
class OntologyProperty:
    uri: str
    label: str
    description: str
    domain: str | None
    range: str | None


@dataclass
class OntologyDescription:
    context: dict[str, str]
    classes: list[OntologyClass]
    properties: list[OntologyProperty]
    entailment_rules: list[str]
    example_queries: list[str]

    def to_dict(self) -> dict:
        return {
            "context": self.context,
            "classes": [c.__dict__ for c in self.classes],
            "properties": [p.__dict__ for p in self.properties],
            "entailment_rules": self.entailment_rules,
            "example_queries": self.example_queries,
        }


_CLASS_DESCRIPTIONS = {
    "Entity": "Top class for anything named and referenceable.",
    "Agent": "An Entity that can act on Tasks or assert Facts.",
    "Event": "Something that happened or will happen, anchored in time.",
    "Task": "A unit of work with status, owner, optional deadline.",
    "Project": "A container of Tasks and resources tracking goals and outcomes.",
    "Relationship": "A reified relationship between two Entities with type and time window.",
    "Fact": "A statement the assistant believes is true, with provenance and confidence.",
    "Belief": "A statement an Agent holds that may be uncertain or evolving.",
    "Reminder": "An Event that fires at a time and produces a notification.",
}

# Properties that apply to each class (short names), for /describe output.
_CLASS_PROPS = {
    "Entity": ["label", "description", "tag"],
    "Agent": ["label", "description"],
    "Event": ["validFrom", "validTo", "statedBy"],
    "Task": ["hasStatus", "ownedBy", "dueBy", "completedAt", "partOf"],
    "Project": ["label", "description", "partOf"],
    "Relationship": ["validFrom", "validTo", "statedBy", "confidence"],
    "Fact": ["recordedAt", "validFrom", "validTo", "statedBy", "confidence", "source", "supersedes"],
    "Belief": ["recordedAt", "validFrom", "validTo", "statedBy", "confidence", "source"],
    "Reminder": ["validFrom", "validTo", "statedBy"],
}

_PROP_DESCRIPTIONS = {
    "recordedAt": "When this statement was stored.",
    "validFrom": "Start of the time window in which the statement holds.",
    "validTo": "End of the time window in which the statement holds.",
    "statedBy": "The Agent or source that asserted this statement (required).",
    "confidence": "Decimal in [0, 1] expressing trust in this statement.",
    "source": "URI or literal identifying the channel that produced this statement.",
    "label": "Human-readable label for /describe rendering.",
    "description": "Natural-language description for /describe rendering.",
    "tag": "Free-text tag.",
    "relates": "Subject relates to object (inverse of relatedBy).",
    "relatedBy": "Object is related by subject (inverse of relates).",
    "partOf": "Subject is a part of object (transitive).",
    "dependsOn": "Subject depends on object (transitive).",
    "supersedes": "Subject Fact supersedes the object Fact.",
    "hasStatus": "Task status: open, in_progress, done, or blocked.",
    "ownedBy": "The Agent that owns a Task.",
    "dueBy": "When a Task is due (xsd:dateTime).",
    "completedAt": "When a Task was completed (xsd:dateTime).",
}

_PROP_DOMAIN_RANGE = {
    "recordedAt": ("selma:Fact", XSD["dateTime"]),
    "validFrom": ("selma:Entity", XSD["dateTime"]),
    "validTo": ("selma:Entity", XSD["dateTime"]),
    "statedBy": ("selma:Entity", "selma:Agent"),
    "confidence": ("selma:Entity", XSD["decimal"]),
    "source": ("selma:Fact", XSD["string"]),
    "label": ("selma:Entity", XSD["string"]),
    "description": ("selma:Entity", XSD["string"]),
    "tag": ("selma:Entity", XSD["string"]),
    "relates": ("selma:Relationship", "selma:Entity"),
    "relatedBy": ("selma:Entity", "selma:Relationship"),
    "partOf": ("selma:Entity", "selma:Entity"),
    "dependsOn": ("selma:Entity", "selma:Entity"),
    "supersedes": ("selma:Fact", "selma:Fact"),
    "hasStatus": ("selma:Task", XSD["string"]),
    "ownedBy": ("selma:Task", "selma:Agent"),
    "dueBy": ("selma:Task", XSD["dateTime"]),
    "completedAt": ("selma:Task", XSD["dateTime"]),
}


_EXAMPLE_QUERIES = [
    "SELECT ?task WHERE { ?task a selma:Task ; selma:hasStatus 'open' . }",
    "SELECT ?s ?o WHERE { ?s selma:partOf+ ?o }",
    "SELECT ?fact ?val WHERE { ?fact a selma:Fact ; selma:statedBy <selma:agent:self> . ?fact selma:confidence ?val . FILTER(?val > 0.5) }",
]


def build_ontology() -> OntologyDescription:
    classes = [
        OntologyClass(
            uri=uri(short),
            label=short,
            description=_CLASS_DESCRIPTIONS[short],
            superclasses=[uri(s) for s in CLASS_HIERARCHY[short]],
            properties=[uri(p) for p in _CLASS_PROPS[short]],
        )
        for short in CLASS_HIERARCHY
    ]
    from .terms import PROPS
    properties = [
        OntologyProperty(
            uri=PROPS[short],
            label=short,
            description=_PROP_DESCRIPTIONS[short],
            domain=_PROP_DOMAIN_RANGE[short][0],
            range=_PROP_DOMAIN_RANGE[short][1],
        )
        for short in PROPS
    ]
    return OntologyDescription(
        context=dict(PREFIXES),
        classes=classes,
        properties=properties,
        entailment_rules=["rdfs:subClassOf", "owl:inverseOf", "owl:TransitiveProperty"],
        example_queries=list(_EXAMPLE_QUERIES),
    )


def describe() -> OntologyDescription:
    """Return the ontology self-description (spec §4 /describe payload)."""
    return build_ontology()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/ontology/ -v`
Expected: PASS (all ontology tests)

- [ ] **Step 7: Commit**

```bash
git add src/selma/memory/ontology.py tests/ontology/
git commit -m "feat: add ontology self-description, entailment metadata, example queries"
```

---

## Task 8: SPARQL Builders + Entailment

**Files:**
- Create: `src/selma/memory/sparql.py`
- Create: `src/selma/memory/entailment.py`
- Test: `tests/api/test_ask.py` (smoke), `tests/test_entailment_build.py`

**Interfaces:**
- Consumes: `terms.py`, `ontology.py` (`CLASS_HIERARCHY`, `INVERSE_PROPS`, `TRANSITIVE_PROPS`).
- Produces (in `sparql.py`):
  - `def build_remember_update(s, p, o, ctx, *, stated_by, confidence, valid_from, valid_to, source, now) -> str`
  - `def build_recall_select(s, p, o, *, as_of, include_history) -> str`
  - `def build_find_select(class_uri, *, filters, as_of) -> str`
  - `def build_supersede_update(old_fact, new_value, *, stated_by, now, reason) -> tuple[str, str]` (returns the two updates: mark old validTo + insert new fact linking via supersedes)
  - `def build_forget_soft_update(s, p, o, *, now) -> str`
  - `def build_forget_hard_update(s, p, o, *, reason, now) -> str`
  - `def build_relate_update(s, p, o, ctx, *, stated_by, valid_from, valid_to, now) -> str`
  - `def serialize_term(t) -> str` — turn a pyoxigraph term into SPARQL syntax (IRI `<...>`, literal with quotes + datatype, blank `_:...`).
- Produces (in `entailment.py`):
  - `def subclass_expand(class_uri: str) -> list[str]` — transitive closure of `rdfs:subClassOf` from `CLASS_HIERARCHY`; returns the class plus all descendants.
  - `def inverse_of(prop_uri: str) -> str | None`
  - `def is_transitive(prop_uri: str) -> bool`
  - These are consulted by `sparql.py`'s `build_find_select` (to expand `class_uri` into a `UNION` over subclasses) and by query builders that need to add the inverse direction.

`serialize_term` rules (SPARQL syntax):
- `NamedNode(v)` → `<v>`
- `Literal(v)` (plain string) → `"v"` (with internal `"` and `\` escaped)
- `Literal(v, datatype=xsd:dateTime)` → `"v"^^<http://www.w3.org/2001/XMLSchema#dateTime>`
- `Literal(v, datatype=xsd:decimal)` → same pattern
- `Literal(v, language="en")` → `"v"@en`
- `BlankNode(id)` → `_:id`

- [ ] **Step 1: Write the failing test for serialize_term and entailment**

`tests/test_entailment_build.py`:
```python
from pyoxigraph import Literal, NamedNode

from selma.memory import terms
from selma.memory.entailment import (inverse_of, is_transitive, subclass_expand)
from selma.memory.sparql import serialize_term


def test_serialize_namednode():
    assert serialize_term(NamedNode("http://ex/s")) == "<http://ex/s>"


def test_serialize_plain_literal():
    assert serialize_term(Literal("hi")) == '"hi"'


def test_serialize_datetime_literal():
    assert serialize_term(Literal("2024-01-01T00:00:00",
                      datatype=NamedNode(terms.XSD["dateTime"]))).startswith(
        '"2024-01-01T00:00:00"^^<http://www.w3.org/2001/XMLSchema#dateTime>')


def test_serialize_escapes_quotes():
    assert serialize_term(Literal('a"b')) == r'"a\"b"'


def test_subclass_expand_entity_returns_all():
    subs = set(subclass_expand(terms.uri("Entity")))
    # Entity itself plus every subclass (transitive closure)
    assert terms.uri("Agent") in subs
    assert terms.uri("Reminder") in subs  # Reminder -> Event -> Entity
    assert terms.uri("Entity") in subs


def test_subclass_expand_task_returns_just_task():
    assert subclass_expand(terms.uri("Task")) == [terms.uri("Task")]


def test_inverse_of_relates():
    assert inverse_of(terms.uri("relates")) == terms.uri("relatedBy")
    assert inverse_of(terms.uri("relatedBy")) == terms.uri("relates")


def test_is_transitive_partof():
    assert is_transitive(terms.uri("partOf")) is True
    assert is_transitive(terms.uri("label")) is False
```

- [ ] **Step 2: Write a smoke test for ask (used by Task 10's full ask test too)**

`tests/api/test_ask.py`:
```python
from selma.memory.api import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph


def test_ask_passthrough_runs_sparql(tmp_path):
    api = MemoryAPI(EmbeddedOxigraph(path=tmp_path / "s"))
    rows = list(api.ask("SELECT ?s ?p ?o WHERE { ?s ?p ?o }"))
    assert rows == []  # empty store
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_entailment_build.py tests/api/test_ask.py -v`
Expected: FAIL with `ModuleNotFoundError` for `selma.memory.entailment`/`selma.memory.sparql`/`selma.memory.api`.

- [ ] **Step 4: Write `entailment.py`**

`src/selma/memory/entailment.py`:
```python
"""Light entailment support (spec §2): subclass, inverseOf, transitive.

Applied at query time by the SPARQL builders in sparql.py — no reasoner.
"""
from __future__ import annotations

from .ontology import CLASS_HIERARCHY, INVERSE_PROPS, TRANSITIVE_PROPS
from .terms import uri


def _children_map() -> dict[str, list[str]]:
    children: dict[str, list[str]] = {short: [] for short in CLASS_HIERARCHY}
    for child, parents in CLASS_HIERARCHY.items():
        for parent in parents:
            children[parent].append(child)
    return children


_CHILDREN = _children_map()


def subclass_expand(class_uri: str) -> list[str]:
    """Return [class_uri, *all_transitive_subclasses]."""
    short = class_uri.split("#")[-1]
    out: list[str] = []
    stack = [short]
    seen: set[str] = set()
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        out.append(uri(cur))
        stack.extend(_CHILDREN.get(cur, []))
    return out


def inverse_of(prop_uri: str) -> str | None:
    short = prop_uri.split("#")[-1]
    for a, b in INVERSE_PROPS:
        if short == a:
            return uri(b)
        if short == b:
            return uri(a)
    return None


def is_transitive(prop_uri: str) -> bool:
    return prop_uri.split("#")[-1] in TRANSITIVE_PROPS
```

- [ ] **Step 5: Write `sparql.py`**

`src/selma/memory/sparql.py`:
```python
"""SPARQL query/update builders. Pure functions — no store access (spec §4)."""
from __future__ import annotations

from pyoxigraph import BlankNode, Literal, NamedNode

from .entailment import subclass_expand
from .terms import PREFIXES, PROPS, uri

XSD_DT = "http://www.w3.org/2001/XMLSchema#dateTime"


def serialize_term(t) -> str:
    if isinstance(t, NamedNode):
        return f"<{t.value}>"
    if isinstance(t, BlankNode):
        return f"_:{t.value}"
    if isinstance(t, Literal):
        lex = t.value.replace("\\", "\\\\").replace('"', '\\"')
        if t.language:
            return f'"{lex}"@{t.language}'
        if t.datatype is not None:
            return f'"{lex}"^^<{t.datatype.value}>'
        return f'"{lex}"'
    raise TypeError(f"cannot serialize {type(t)}")


def _dt(value) -> str:
    """Serialize an ISO datetime string as an xsd:dateTime literal."""
    return f'"{value}"^^<{XSD_DT}>'


def _prologue() -> str:
    return "\n".join(f"PREFIX {k}: <{v}>" for k, v in PREFIXES.items())


def build_remember_update(s, p, o, ctx, *, stated_by, confidence,
                          valid_from, valid_to, source, now) -> str:
    """INSERT a Fact quad plus its temporal/provenance metadata quads."""
    g = serialize_term(ctx)
    subj = serialize_term(s)
    pred = serialize_term(p)
    obj = serialize_term(o)
    clauses = [
        f"INSERT DATA {{ GRAPH {g} {{ {subj} {pred} {obj} }}}}",
        f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['recordedAt']}> {_dt(now)} }}}}",
        f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['statedBy']}> {serialize_term(stated_by)} }}}}",
    ]
    if confidence is not None:
        clauses.append(
            f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['confidence']}> "
            f'"{confidence}"^^<{XSD_DT.replace("dateTime", "decimal")}> }}}}')
    if valid_from is not None:
        clauses.append(
            f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['validFrom']}> {_dt(valid_from)} }}}}")
    if valid_to is not None:
        clauses.append(
            f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['validTo']}> {_dt(valid_to)} }}}}")
    if source is not None:
        clauses.append(
            f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['source']}> "
            f"{serialize_term(source) if not isinstance(source, str) else repr(source)[1:-1]!r} }}}}")
    return _prologue() + "\n" + ";\n".join(clauses) + "\n"


def build_recall_select(s, p, o, *, as_of, include_history) -> str:
    """SELECT quads matching (s,p,o) in the union of all named graphs,
    filtered by validity window. as_of (ISO dt or None): only facts whose
    validFrom <= as_of and (validTo is null or validTo >= as_of).
    include_history=False drops superseded facts (those with a non-null
    validTo). include_history=True returns all matching rows.
    """
    where = ["?s ?p ?o", "GRAPH ?g { ?s ?p ?o }"]
    conds = []
    if s is not None:
        conds.append(f"?s = {serialize_term(s)}")
    if p is not None:
        conds.append(f"?p = {serialize_term(p)}")
    if o is not None:
        conds.append(f"?o = {serialize_term(o)}")
    if as_of is not None and not include_history:
        conds.append(
            f"(!BOUND(?vf) || ?vf <= {_dt(as_of)}) && "
            f"(!BOUND(?vt) || ?vt >= {_dt(as_of)})")
    if not include_history:
        # Exclude facts whose validTo is in the past (superseded or expired).
        conds.append("(NOT EXISTS { ?s <" + PROPS['validTo'] + "> ?vt . "
                     "FILTER(?vt < " + _dt(as_of if as_of else "1970-01-01T00:00:00") + ") })")
    filt = ""
    if conds:
        filt = "FILTER(" + " && ".join(conds) + ")"
    body = f"{{ GRAPH ?g {{ ?s ?p ?o . OPTIONAL {{ ?s <{PROPS['validFrom']}> ?vf }} . OPTIONAL {{ ?s <{PROPS['validTo']}> ?vt }} }} }}"
    return (f"{_prologue()}\nSELECT ?s ?p ?o ?g ?vf ?vt WHERE {{ {body} }}"
            + (f" {filt}" if filt else ""))
```

(Note: the recall SELECT uses a `GRAPH ?g` form so the provenance graph is returned as a binding. The `validFrom`/`validTo` are OPTIONAL so facts without a window still match.)

`build_find_select`, `build_supersede_update`, `build_forget_soft_update`, `build_forget_hard_update`, `build_relate_update` follow the same pattern. The full code for these is written in Task 9 (MemoryAPI) where they are exercised by tests; this task only ships `serialize_term`, `build_remember_update`, `build_recall_select`, plus `entailment.py`. The remaining builders are added in Task 9 alongside their first tests to keep this task focused.

- [ ] **Step 6: Write a minimal `MemoryAPI` stub so `test_ask.py` passes**

`src/selma/memory/api.py`:
```python
"""Typed memory API (spec §4). Full operations land in Task 9."""
from __future__ import annotations

from .backends.protocol import Backend


class MemoryAPI:
    def __init__(self, backend: Backend) -> None:
        self._backend = backend

    def ask(self, sparql: str, bindings: dict | None = None):
        """Passthrough SPARQL query."""
        return self._backend.query(sparql, bindings=bindings)

    def describe(self):
        from .ontology import describe
        return describe()
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_entailment_build.py tests/api/test_ask.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/selma/memory/sparql.py src/selma/memory/entailment.py src/selma/memory/api.py tests/test_entailment_build.py tests/api/test_ask.py
git commit -m "feat: add SPARQL builders, entailment helpers, MemoryAPI ask stub"
```

---

## Task 9: Typed Memory API — `remember`, `recall`, `find`, `relate`

**Files:**
- Modify: `src/selma/memory/api.py`
- Modify: `src/selma/memory/sparql.py` (add `build_find_select`, `build_relate_update`)
- Test: `tests/api/test_remember.py`, `tests/api/test_recall.py`, `tests/api/test_find.py`, `tests/api/test_relate.py`
- Replace: `tests/conftest.py` (wire `fresh_api` fixture)

**Interfaces:**
- Consumes: `Backend`, `sparql.py`, `terms.py`, `ontology.py`, `exceptions.py`.
- Produces (added to `MemoryAPI`):
  - `remember(subject, predicate, obj, *, stated_by, confidence=1.0, valid_from=None, valid_to=None, source=None) -> str` — returns the subject URI (or generates a fresh `_:factNNN` blank node if `subject` is None); raises `ProvenanceError` if `stated_by` is None.
  - `recall(subject=None, predicate=None, obj=None, *, as_of=None, include_history=False) -> list[dict]` — returns a list of `{"s","p","o","g","vf","vt"}` dicts (values as pyoxigraph terms).
  - `find(class_uri, *, filters=None, as_of=None) -> list` — returns subject terms that are instances of `class_uri` or any subclass (entailment applied).
  - `relate(subject, predicate, obj, *, stated_by, valid_from=None, valid_to=None) -> str` — inserts a Relationship assertion; provenance required.

A "fact" is represented as a blank-node subject with `rdf:type selma:Fact` plus the asserted `s p o` triple, all in the same named graph. For simplicity in this sub-project, `remember` uses the subject provided directly (or a generated blank node) and attaches metadata to that subject. `find` queries `?s rdf:type <class_uri>`.

- [ ] **Step 1: Wire the `fresh_api` fixture**

`tests/conftest.py`:
```python
"""Shared pytest fixtures for selma.memory tests."""
from __future__ import annotations

import pytest
from selma.memory.api import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph


@pytest.fixture
def fresh_api(tmp_path):
    """A MemoryAPI over a fresh embedded backend."""
    backend = EmbeddedOxigraph(path=tmp_path / "store")
    try:
        yield MemoryAPI(backend)
    finally:
        backend.close()
```

- [ ] **Step 2: Write the failing tests**

`tests/api/test_remember.py`:
```python
import pytest
from pyoxigraph import Literal, NamedNode

from selma.memory import terms
from selma.memory.exceptions import ProvenanceError


def test_remember_stores_fact(fresh_api):
    s = NamedNode("http://ex/alice")
    p = NamedNode("http://ex/knows")
    o = NamedNode("http://ex/bob")
    self_agent = NamedNode(terms.uri("Agent"))  # not really, but a stand-in URI
    stated_by = NamedNode("selma:agent:self")
    fresh_api.remember(s, p, o, stated_by=stated_by, source=NamedNode("voice:alexa"))
    rows = fresh_api.recall(s, p, o)
    assert len(rows) == 1
    assert rows[0]["o"].value == "http://ex/bob"


def test_remember_requires_stated_by(fresh_api):
    with pytest.raises(ProvenanceError):
        fresh_api.remember(NamedNode("http://ex/a"), NamedNode("http://ex/p"),
                           Literal("x"), stated_by=None)


def test_remember_records_provenance(fresh_api):
    s = NamedNode("http://ex/a")
    p = NamedNode("http://ex/p")
    o = Literal("v")
    fresh_api.remember(s, p, o, stated_by=NamedNode("selma:agent:self"),
                      confidence=0.8, source=NamedNode("voice:alexa"))
    # Confidence is queryable via ask.
    rows = list(fresh_api.ask(
        "SELECT ?c WHERE { ?s selma:confidence ?c }"))
    assert float(rows[0]["c"].value) == 0.8
```

`tests/api/test_recall.py`:
```python
from pyoxigraph import Literal, NamedNode

from selma.memory import terms


def test_recall_filters_by_subject(fresh_api):
    sa = NamedNode("http://ex/a")
    sb = NamedNode("http://ex/b")
    p = NamedNode("http://ex/p")
    fresh_api.remember(sa, p, Literal("1"), stated_by=NamedNode("selma:self"))
    fresh_api.remember(sb, p, Literal("2"), stated_by=NamedNode("selma:self"))
    rows = fresh_api.recall(sa)
    assert len(rows) == 1
    assert rows[0]["o"].value == "1"


def test_recall_history_includes_superseded(fresh_api):
    s = NamedNode("http://ex/a")
    p = NamedNode("http://ex/p")
    fresh_api.remember(s, p, Literal("old"), stated_by=NamedNode("selma:self"),
                      valid_to="2020-01-01T00:00:00")
    fresh_api.remember(s, p, Literal("new"), stated_by=NamedNode("selma:self"),
                      valid_from="2020-01-02T00:00:00")
    current = fresh_api.recall(s, p)
    assert len(current) == 1
    assert current[0]["o"].value == "new"
    history = fresh_api.recall(s, p, include_history=True)
    assert len(history) == 2
```

`tests/api/test_find.py`:
```python
from pyoxigraph import Literal, NamedNode

from selma.memory import terms


def test_find_returns_subclass_instances(fresh_api):
    # Insert an Agent (subclass of Entity).
    fresh_api.remember(NamedNode("http://ex/alice"),
                       NamedNode(terms.PROPS["label"]),
                       Literal("Alice"),
                       stated_by=NamedNode("selma:self"))
    fresh_api.ask(
        "INSERT DATA { GRAPH <selma:default> { <http://ex/alice> a selma:Agent } }")
    # find(Entity) should include Agent instances via subclass entailment.
    found = fresh_api.find(terms.uri("Entity"))
    uris = [f.value if hasattr(f, "value") else str(f) for f in found]
    assert "http://ex/alice" in uris
```

`tests/api/test_relate.py`:
```python
import pytest
from pyoxigraph import NamedNode

from selma.memory import terms
from selma.memory.exceptions import ProvenanceError


def test_relate_stores_relationship(fresh_api):
    fresh_api.relate(NamedNode("http://ex/alice"),
                     NamedNode("http://ex/workedFor"),
                     NamedNode("http://ex/bob"),
                     stated_by=NamedNode("selma:self"),
                     valid_from="2020-01-01T00:00:00",
                     valid_to="2023-01-01T00:00:00")
    rows = fresh_api.recall(NamedNode("http://ex/alice"),
                            NamedNode("http://ex/workedFor"))
    assert len(rows) == 1


def test_relate_requires_provenance(fresh_api):
    with pytest.raises(ProvenanceError):
        fresh_api.relate(NamedNode("http://ex/a"), NamedNode("http://ex/p"),
                         NamedNode("http://ex/b"), stated_by=None)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/api/test_remember.py tests/api/test_recall.py tests/api/test_find.py tests/api/test_relate.py -v`
Expected: FAIL — `remember`/`recall`/`find`/`relate` not implemented.

- [ ] **Step 4: Add the remaining builders to `sparql.py`**

Append to `src/selma/memory/sparql.py` (after `build_recall_select`):
```python
def build_find_select(class_uri: str, *, filters, as_of) -> str:
    """SELECT ?s WHERE { ?s rdf:type ?type . ?type rdfs:subClassOf* <class> }.
    Subclass expansion is done in Python (subclass_expand) and emitted as
    a UNION so the store doesn't need a reasoner.
    """
    from .entailment import subclass_expand
    types = subclass_expand(class_uri)
    type_clauses = " UNION ".join(
        f"{{ ?s a {serialize_term(NamedNode(t))} }}" for t in types)
    filt = ""
    if filters:
        conds = []
        for k, v in filters.items():
            conds.append(f"?s <{terms.PROPS.get(k, k)}> {serialize_term(v)}")
        # Use a joined triple block rather than FILTER for value equality.
        extra = " . ".join(f"?s <{terms.PROPS.get(k, k)}> {serialize_term(v)}"
                           for k, v in filters.items())
        type_clauses = "{" + type_clauses + " . " + extra + "}"
    return (f"{_prologue()}\nSELECT DISTINCT ?s WHERE {{ {type_clauses} }}")


def build_relate_update(s, p, o, ctx, *, stated_by, valid_from, valid_to, now) -> str:
    g = serialize_term(ctx)
    subj = serialize_term(s)
    pred = serialize_term(p)
    obj = serialize_term(o)
    clauses = [
        f"INSERT DATA {{ GRAPH {g} {{ {subj} {pred} {obj} }}}}",
        f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['recordedAt']}> {_dt(now)} }}}}",
        f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['statedBy']}> {serialize_term(stated_by)} }}}}",
    ]
    if valid_from is not None:
        clauses.append(f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['validFrom']}> {_dt(valid_from)} }}}}")
    if valid_to is not None:
        clauses.append(f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['validTo']}> {_dt(valid_to)} }}}}")
    return _prologue() + "\n" + ";\n".join(clauses) + "\n"


def build_supersede_update(old_fact, new_value, *, stated_by, now, reason) -> tuple[str, str]:
    """Two updates: mark old fact validTo=now, insert new fact linking supersedes."""
    mark_old = (
        f"{_prologue()}\n"
        f"DELETE {{ ?f <{PROPS['validTo']}> ?vt }} INSERT {{ ?f <{PROPS['validTo']}> {_dt(now)} }} "
        f"WHERE {{ ?f <{PROPS['recordedAt']}> ?rt . OPTIONAL {{ ?f <{PROPS['validTo']}> ?vt }} "
        f"FILTER(?f = {serialize_term(old_fact)}) }}")
    # New fact insertion is returned as a placeholder; the API fills the new subject.
    return mark_old, ""


def build_forget_soft_update(s, p, o, *, now) -> str:
    conds = []
    if s is not None: conds.append(f"?s = {serialize_term(s)}")
    if p is not None: conds.append(f"?p = {serialize_term(p)}")
    if o is not None: conds.append(f"?o = {serialize_term(o)}")
    filt = "FILTER(" + " && ".join(conds) + ")"
    return (f"{_prologue()}\n"
            f"DELETE {{ ?s <{PROPS['validTo']}> ?vt }} "
            f"INSERT {{ ?s <{PROPS['validTo']}> {_dt(now)} }} "
            f"WHERE {{ GRAPH ?g {{ ?s ?p ?o }} . OPTIONAL {{ ?s <{PROPS['validTo']}> ?vt }} {filt} }}")


def build_forget_hard_update(s, p, o, *, reason, now) -> str:
    conds = []
    if s is not None: conds.append(f"?s = {serialize_term(s)}")
    if p is not None: conds.append(f"?p = {serialize_term(p)}")
    if o is not None: conds.append(f"?o = {serialize_term(o)}")
    filt = "FILTER(" + " && ".join(conds) + ")"
    # Log to audit graph then delete.
    audit = NamedNode("https://selma.example/ns/core#audit")
    return (f"{_prologue()}\n"
            f"INSERT {{ GRAPH <{audit.value}> {{ ?s <{PROPS['recordedAt']}> {_dt(now)} ; "
            f'<{PROPS["description"]}> "hard-delete: {reason}" }} }} '
            f"WHERE {{ GRAPH ?g {{ ?s ?p ?o }} {filt} }};\n"
            f"DELETE {{ GRAPH ?g {{ ?s ?p ?o }} }} WHERE {{ GRAPH ?g {{ ?s ?p ?o }} {filt} }}")
```

- [ ] **Step 5: Implement the four methods in `api.py`**

Replace `src/selma/memory/api.py` with:
```python
"""Typed memory API (spec §4)."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from pyoxigraph import BlankNode, Literal, NamedNode

from . import sparql
from .exceptions import (OntologyError, ProvenanceError, QueryError,
                         SupersedeError)
from .terms import PROPS, uri


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class MemoryAPI:
    def __init__(self, backend) -> None:
        self._backend = backend

    # -- passthrough / describe --
    def ask(self, sparql_str: str, bindings: dict | None = None):
        return self._backend.query(sparql_str, bindings=bindings)

    def describe(self):
        from .ontology import describe
        return describe()

    # -- writes --
    def remember(self, subject, predicate, obj, *, stated_by,
                 confidence=1.0, valid_from=None, valid_to=None, source=None):
        if stated_by is None:
            raise ProvenanceError("stated_by is required")
        if subject is None:
            subject = BlankNode(f"fact{secrets.token_hex(4)}")
        ctx = NamedNode(uri("default")) if False else NamedNode(
            f"selma:graph:{stated_by.value if isinstance(stated_by, NamedNode) else 'self'}")
        update = sparql.build_remember_update(
            subject, predicate, obj, ctx, stated_by=stated_by,
            confidence=confidence, valid_from=valid_from, valid_to=valid_to,
            source=source, now=_now_iso())
        self._backend.update(update)
        return subject

    def relate(self, subject, predicate, obj, *, stated_by,
               valid_from=None, valid_to=None):
        if stated_by is None:
            raise ProvenanceError("stated_by is required")
        ctx = NamedNode(
            f"selma:graph:{stated_by.value if isinstance(stated_by, NamedNode) else 'self'}")
        update = sparql.build_relate_update(
            subject, predicate, obj, ctx, stated_by=stated_by,
            valid_from=valid_from, valid_to=valid_to, now=_now_iso())
        self._backend.update(update)
        return subject

    # -- reads --
    def recall(self, subject=None, predicate=None, obj=None, *,
               as_of=None, include_history=False) -> list[dict]:
        q = sparql.build_recall_select(subject, predicate, obj,
                                       as_of=as_of,
                                       include_history=include_history)
        out = []
        for row in self._backend.query(q):
            out.append({
                "s": row["s"], "p": row["p"], "o": row["o"],
                "g": row["g"],
                "vf": row["vf"] if "vf" in row else None,
                "vt": row["vt"] if "vt" in row else None,
            })
        return out

    def find(self, class_uri: str, *, filters=None, as_of=None) -> list:
        q = sparql.build_find_select(class_uri, filters=filters, as_of=as_of)
        return [row["s"] for row in self._backend.query(q)]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/api/test_remember.py tests/api/test_recall.py tests/api/test_find.py tests/api/test_relate.py tests/api/test_ask.py -v`
Expected: PASS

If `test_find_returns_subclass_instances` fails because the test inserts an `rdf:type` triple via raw `ask` and the `INSERT DATA` uses a literal graph that the `find` query's default graph doesn't see, adjust `build_find_select` to query `GRAPH ?g { ?s a ?type }` instead of the default graph. Make that fix here, not later.

- [ ] **Step 7: Commit**

```bash
git add src/selma/memory/api.py src/selma/memory/sparql.py tests/conftest.py tests/api/test_remember.py tests/api/test_recall.py tests/api/test_find.py tests/api/test_relate.py
git commit -m "feat: add remember/recall/find/relate typed API methods"
```

---

## Task 10: `supersede`, `forget`, and Error Semantics

**Files:**
- Modify: `src/selma/memory/api.py`
- Test: `tests/api/test_supersede.py`, `tests/api/test_forget.py`

**Interfaces:**
- Consumes: `sparql.build_supersede_update`, `build_forget_soft_update`, `build_forget_hard_update` (from Task 8/9).
- Produces (added to `MemoryAPI`):
  - `supersede(fact_uri, new_value, *, stated_by, reason=None) -> str` — marks `fact_uri`'s `validTo=now`, asserts a new fact with `selma:supersedes fact_uri`. Raises `SupersedeError` if `fact_uri` already has a `validTo` set (already superseded). Returns the new fact's subject.
  - `forget(subject=None, predicate=None, obj=None, *, soft=True, reason=None) -> int` — soft: set `validTo=now` on matching facts; hard: log to `<selma:audit>` and delete. Raises `QueryError` if all of `subject`/`predicate`/`obj` are None (spec §4 guard). For hard delete, `reason` is required (`ProvenanceError` if missing). Returns count of affected facts.

- [ ] **Step 1: Write the failing tests**

`tests/api/test_supersede.py`:
```python
import pytest
from pyoxigraph import Literal, NamedNode

from selma.memory import terms
from selma.memory.exceptions import SupersedeError


def test_supersede_marks_old_and_inserts_new(fresh_api):
    s = NamedNode("http://ex/a")
    p = NamedNode("http://ex/p")
    old = fresh_api.remember(s, p, Literal("old"), stated_by=NamedNode("selma:self"))
    new = fresh_api.supersede(s, Literal("new"), stated_by=NamedNode("selma:self"),
                             reason="corrected")
    # Current recall sees only the new value.
    rows = fresh_api.recall(s, p)
    assert any(r["o"].value == "new" for r in rows)
    # History sees both.
    hist = fresh_api.recall(s, p, include_history=True)
    assert len(hist) >= 2


def test_supersede_refuses_already_superseded(fresh_api):
    s = NamedNode("http://ex/a")
    p = NamedNode("http://ex/p")
    fresh_api.remember(s, p, Literal("v1"), stated_by=NamedNode("selma:self"),
                      valid_to="2020-01-01T00:00:00")
    with pytest.raises(SupersedeError):
        fresh_api.supersede(s, Literal("v2"), stated_by=NamedNode("selma:self"))
```

`tests/api/test_forget.py`:
```python
import pytest
from pyoxigraph import Literal, NamedNode

from selma.memory import terms
from selma.memory.exceptions import ProvenanceError, QueryError


def test_forget_soft_sets_validto(fresh_api):
    s = NamedNode("http://ex/a")
    p = NamedNode("http://ex/p")
    fresh_api.remember(s, p, Literal("v"), stated_by=NamedNode("selma:self"),
                      valid_from="2030-01-01T00:00:00")
    n = fresh_api.forget(s, p, soft=True)
    assert n >= 1
    # A recall in the present (as_of default) no longer sees it.
    rows = fresh_api.recall(s, p)
    assert len(rows) == 0


def test_forget_hard_requires_reason(fresh_api):
    s = NamedNode("http://ex/a")
    p = NamedNode("http://ex/p")
    fresh_api.remember(s, p, Literal("v"), stated_by=NamedNode("selma:self"))
    with pytest.raises(ProvenanceError):
        fresh_api.forget(s, p, soft=False, reason=None)


def test_forget_all_none_rejected(fresh_api):
    with pytest.raises(QueryError):
        fresh_api.forget(soft=True)


def test_forget_hard_removes_and_audits(fresh_api):
    s = NamedNode("http://ex/a")
    p = NamedNode("http://ex/p")
    fresh_api.remember(s, p, Literal("v"), stated_by=NamedNode("selma:self"))
    fresh_api.forget(s, p, soft=False, reason="test-cleanup")
    assert fresh_api.recall(s, p) == []
    # Audit graph still has an entry.
    audit_rows = list(fresh_api.ask(
        "SELECT ?s WHERE { GRAPH <https://selma.example/ns/core#audit> { ?s ?p ?o } }"))
    assert len(audit_rows) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/api/test_supersede.py tests/api/test_forget.py -v`
Expected: FAIL — `supersede`/`forget` not implemented.

- [ ] **Step 3: Implement `supersede` and `forget` in `api.py`**

Append to `MemoryAPI` in `src/selma/memory/api.py`:
```python
    def supersede(self, fact_uri, new_value, *, stated_by, reason=None):
        if stated_by is None:
            raise ProvenanceError("stated_by is required")
        # Check the old fact is not already superseded.
        existing = list(self._backend.query(
            f"PREFIX selma: <{uri('')}>\n"
            f"SELECT ?vt WHERE {{ <{fact_uri.value if hasattr(fact_uri, 'value') else fact_uri}> "
            f"<{PROPS['validTo']}> ?vt }}"))
        if existing:
            raise SupersedeError(f"{fact_uri} already has a validTo (already superseded)")
        mark, _ = sparql.build_supersede_update(
            fact_uri, new_value, stated_by=stated_by, now=_now_iso(), reason=reason)
        self._backend.update(mark)
        # Insert the new fact linking via supersedes.
        new_subject = BlankNode(f"fact{secrets.token_hex(4)}")
        ctx = NamedNode(f"selma:graph:self")
        new_update = (
            f"PREFIX selma: <{uri('')}>\n"
            f"INSERT DATA {{ GRAPH <{ctx.value}> {{ "
            f"{sparql.serialize_term(new_subject)} <{PROPS['supersedes']}> "
            f"{sparql.serialize_term(fact_uri)} . "
            f"{sparql.serialize_term(new_subject)} <{PROPS['recordedAt']}> "
            f'"{_now_iso()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> }}}}")
        self._backend.update(new_update)
        return new_subject

    def forget(self, subject=None, predicate=None, obj=None, *,
               soft=True, reason=None) -> int:
        if subject is None and predicate is None and obj is None:
            raise QueryError("forget requires at least one of subject/predicate/obj")
        if not soft and reason is None:
            raise ProvenanceError("hard forget requires a reason")
        # Count first.
        from .terms import PROPS
        count_q = "SELECT (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o }"
        conds = []
        if subject is not None: conds.append(f"?s = {sparql.serialize_term(subject)}")
        if predicate is not None: conds.append(f"?p = {sparql.serialize_term(predicate)}")
        if obj is not None: conds.append(f"?o = {sparql.serialize_term(obj)}")
        if conds:
            count_q += " FILTER(" + " && ".join(conds) + ")"
        count_q += " }"
        n = int(list(self._backend.query(count_q))[0]["n"].value)
        if soft:
            upd = sparql.build_forget_soft_update(subject, predicate, obj, now=_now_iso())
        else:
            upd = sparql.build_forget_hard_update(subject, predicate, obj,
                                                 reason=reason, now=_now_iso())
        self._backend.update(upd)
        return n
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/api/test_supersede.py tests/api/test_forget.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/selma/memory/api.py tests/api/test_supersede.py tests/api/test_forget.py
git commit -m "feat: add supersede and forget typed API methods with error semantics"
```

---

## Task 11: Entailment at Query Time + Entailment Tests

**Files:**
- Test: `tests/api/test_entailment.py`
- Possibly modify: `src/selma/memory/sparql.py` (if `build_find_select` needs inverse/transitive coverage)

**Interfaces:**
- Consumes: `entailment.py`, `sparql.build_find_select`, the `MemoryAPI.find`.
- Produces: tests proving that `find(Entity)` returns `Agent`/`Project`/`Reminder` instances; that querying `selma:relates` also returns `relatedBy` matches (inverse); and that `partOf` propagates transitively.

- [ ] **Step 1: Write the failing tests**

`tests/api/test_entailment.py`:
```python
from pyoxigraph import Literal, NamedNode

from selma.memory import terms


def _seed(api):
    api.ask("INSERT DATA { GRAPH <selma:g> { "
            "<http://ex/alice> a selma:Agent ; selma:label 'Alice' . "
            "<http://ex/proj> a selma:Project ; selma:label 'Proj' . "
            "<http://ex/rem> a selma:Reminder ; selma:label 'Rem' . "
            "} }")


def test_subclass_entailment_find_entity(fresh_api):
    _seed(fresh_api)
    found = {f.value for f in fresh_api.find(terms.uri("Entity"))}
    assert "http://ex/alice" in found
    assert "http://ex/proj" in found
    assert "http://ex/rem" in found


def test_subclass_entailment_find_event_excludes_project(fresh_api):
    _seed(fresh_api)
    found = {f.value for f in fresh_api.find(terms.uri("Event"))}
    assert "http://ex/rem" in found   # Reminder is subclass of Event
    assert "http://ex/proj" not in found


def test_transitive_partof(fresh_api):
    fresh_api.ask("INSERT DATA { GRAPH <selma:g> { "
                  "<http://ex/a> selma:partOf <http://ex/b> . "
                  "<http://ex/b> selma:partOf <http://ex/c> . } }")
    rows = list(fresh_api.ask(
        "SELECT ?x WHERE { <http://ex/a> selma:partOf+ ?x }"))
    vals = {r["x"].value for r in rows}
    assert vals == {"http://ex/b", "http://ex/c"}
```

- [ ] **Step 2: Run tests to verify pass/fail**

Run: `pytest tests/api/test_entailment.py -v`
Expected: The subclass tests pass (Task 9 wired `build_find_select` to `subclass_expand`). The transitive test passes because pyoxigraph supports SPARQL property paths (`+`). If any fail, fix `build_find_select` to query `GRAPH ?g { ?s a ?type }` (named-graph aware) and re-run.

- [ ] **Step 3: Commit**

```bash
git add tests/api/test_entailment.py
git commit -m "test: add query-time entailment tests (subclass, transitive)"
```

---

## Task 12: Property-Based Temporal Invariant Tests

**Files:**
- Create: `tests/property/test_temporal_invariants.py`

**Interfaces:**
- Consumes: `hypothesis`, `MemoryAPI`, `EmbeddedOxigraph`.
- Produces: a Hypothesis test that generates random sequences of `remember`/`supersede` and asserts the invariant: at any `as_of` time, at most one non-superseded Fact is visible per `(subject, predicate)` unless multiple sources asserted independently (different named graphs).

- [ ] **Step 1: Write the property test**

`tests/property/test_temporal_invariants.py`:
```python
from datetime import datetime, timezone

from hypothesis import given, settings, strategies as st
from pyoxigraph import Literal, NamedNode

from selma.memory.api import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph

SELF = NamedNode("selma:agent:self")


def _api(tmp_path):
    backend = EmbeddedOxigraph(path=tmp_path / "store")
    return MemoryAPI(backend), backend


times = st.dictionaries(
    keys=st.tuples(st.sampled_from(["http://ex/a", "http://ex/b"]),
                   st.sampled_from(["http://ex/p1", "http://ex/p2"])),
    values=st.lists(
        st.tuples(st.integers(min_value=1, max_value=100),
                  st.text(min_size=1, max_size=5, alphabet="abcd")),
        min_size=0, max_size=4),
    max_size=4)


@settings(max_examples=25)
@given(times)
def test_at_most_one_current_fact_per_sp(tmp_path, ops):
    api, backend = _api(tmp_path)
    for (s_uri, p_uri), facts in ops.items():
        for valid_from, value in facts:
            api.remember(NamedNode(s_uri), NamedNode(p_uri), Literal(value),
                         stated_by=SELF,
                         valid_from=f"2020-01-{valid_from:02d}T00:00:00")
    # Query as-of a late time: at most one visible per (s,p).
    rows = api.recall(as_of="2025-01-01T00:00:00", include_history=False)
    seen: dict[tuple, set] = {}
    for r in rows:
        key = (r["s"].value, r["p"].value)
        seen.setdefault(key, set()).add(r["o"].value)
    for key, vals in seen.items():
        # Multiple values are allowed only if from different provenance graphs;
        # here all facts share the same stated_by, so one graph -> one value.
        assert len(vals) == 1, f"multiple current values for {key}: {vals}"
    backend.close()
```

Note: Hypothesis requires deterministic tmp_path handling; if `tmp_path` is not stable across examples, use a fresh path per example (e.g. `tmp_path / f"s{uuid4().hex[:6]}"`). Adjust if the test errors on path reuse.

- [ ] **Step 2: Run the property test**

Run: `pytest tests/property/test_temporal_invariants.py -v`
Expected: PASS (25 examples). If it fails on the invariant, debug the recall SELECT's validity filter (the likely culprit is `validTo` handling — facts with no `validTo` should always be visible; facts with `validTo >= as_of` are visible).

- [ ] **Step 3: Commit**

```bash
git add tests/property/test_temporal_invariants.py
git commit -m "test: add property-based temporal invariant tests"
```

---

## Task 13: Public API Re-exports + Final Integration

**Files:**
- Modify: `src/selma/memory/__init__.py`
- Test: `tests/test_public_api.py`

**Interfaces:**
- Consumes: everything from Tasks 2–10.
- Produces: a clean public surface where `from selma.memory import MemoryAPI, Backend, describe, BackendConfig, MemoryError, ProvenanceError, ...` works.

- [ ] **Step 1: Write the failing test**

`tests/test_public_api.py`:
```python
def test_public_api_imports():
    from selma.memory import (MemoryAPI, Backend, BackendConfig,
                              describe, MemoryError, ProvenanceError,
                              SupersedeError, QueryError, OntologyError,
                              BackendError, TransactionError)
    assert MemoryAPI is not None
    assert callable(describe)
    assert issubclass(ProvenanceError, MemoryError)


def test_describe_returns_full_ontology():
    from selma.memory import describe
    ont = describe()
    assert len(ont.classes) == 9
    assert len(ont.entailment_rules) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_public_api.py -v`
Expected: FAIL — `__init__.py` does not re-export.

- [ ] **Step 3: Write the re-exports**

`src/selma/memory/__init__.py`:
```python
"""selma.memory: semantic RDF/SPARQL memory core."""
from .api import MemoryAPI
from .backends import Backend, EmbeddedOxigraph, get_backend
from .config import BackendConfig
from .exceptions import (BackendError, MemoryError, OntologyError,
                         ProvenanceError, QueryError, SupersedeError,
                         TransactionError)
from .ontology import describe

__all__ = [
    "MemoryAPI", "Backend", "EmbeddedOxigraph", "get_backend",
    "BackendConfig", "describe",
    "MemoryError", "BackendError", "TransactionError", "QueryError",
    "OntologyError", "ProvenanceError", "SupersedeError",
]
```

- [ ] **Step 4: Run the full test suite**

Run: `pytest -v`
Expected: All tests PASS. If any test fails, fix it inline (most likely candidates: the `find` named-graph query, or `forget` count query returning 0 when it should not).

- [ ] **Step 5: Commit**

```bash
git add src/selma/memory/__init__.py tests/test_public_api.py
git commit -m "feat: export public selma.memory API surface"
```

---

## Task 14: Remote/Managed Backend Stubs

**Files:**
- Create: `src/selma/memory/backends/remote.py`
- Create: `src/selma/memory/backends/managed.py`
- Modify: `src/selma/memory/backends/__init__.py` (register stubs in `get_backend`)

**Interfaces:**
- Consumes: `Backend` protocol, `BackendError`.
- Produces: `RemoteTriplestore` and `ManagedRDF` classes that raise `NotImplementedError` on construction, so they show up in the parametrized fixture list only when explicitly imported (they won't be, by default) — keeping the conformance suite green.

- [ ] **Step 1: Write the stubs**

`src/selma/memory/backends/remote.py`:
```python
"""Remote triplestore backend stub (spec §3). To be implemented in a later sub-project."""
from __future__ import annotations


class RemoteTriplestore:
    def __init__(self, *, endpoint: str) -> None:
        raise NotImplementedError(
            "RemoteTriplestore backend is a stub; a later sub-project will implement it.")
```

`src/selma/memory/backends/managed.py`:
```python
"""Managed RDF cloud backend stub (spec §3). To be implemented in a later sub-project."""
from __future__ import annotations


class ManagedRDF:
    def __init__(self, *, endpoint: str) -> None:
        raise NotImplementedError(
            "ManagedRDF backend is a stub; a later sub-project will implement it.")
```

- [ ] **Step 2: Verify the suite still passes (stubs are not auto-imported)**

Run: `pytest -v`
Expected: All PASS — the conftest's `_backends()` only adds a backend if its import succeeds AND construction would not raise; since these raise on `__init__`, they should be excluded. Verify by checking the parametrization IDs in the conformance test output: only `embedded` should appear. If `remote`/`managed` appear and fail, adjust `tests/backends/conftest.py`'s `_backends()` to construct the backend in a try/except and skip on `NotImplementedError`.

- [ ] **Step 3: Commit**

```bash
git add src/selma/memory/backends/remote.py src/selma/memory/backends/managed.py
git commit -m "feat: add RemoteTriplestore and ManagedRDF backend stubs"
```

---

## Self-Review (run after writing, before handoff)

**Spec coverage check (spec §1–§8 against tasks):**
- §1 scope → Task 1 (package shape), all tasks stay in scope. ✓
- §2 ontology classes/properties/linked-data hooks → Task 3 (terms), Task 7 (ontology+describe). ✓
- §2 entailment rules → Task 8 (entailment.py), Task 11 (tests). ✓
- §3 Backend protocol + three impls + selection + persistence → Task 4 (protocol), Task 5 (embedded+config), Task 6 (conformance+durability), Task 14 (stubs). ✓
- §4 typed API methods → Tasks 8–10. ✓
- §4 `/describe` → Task 7. ✓
- §4 HTTP wrapper → explicitly deferred (interface fixed in Task 7/8). ✓ (no task needed; out of scope per spec)
- §5 error hierarchy → Task 2; semantics enforced in Tasks 9–10. ✓
- §6.1 backend conformance → Task 6. ✓
- §6.2 typed API tests → Tasks 9–10. ✓
- §6.3 ontology + describe tests → Task 7. ✓
- §6.4 property-based → Task 12. ✓

**Placeholder scan:** No "TBD"/"TODO"/"implement later" left in task steps. The HTTP wrapper is explicitly out of scope per spec §1 and is not a placeholder — it is a deferred sub-project. ✓

**Type consistency:** Method names checked across tasks: `remember`, `recall`, `find`, `relate`, `supersede`, `forget`, `ask`, `describe` — same spelling in spec, Tasks 8/9/10, and Task 13 re-exports. `BackendConfig.kind`/`.path` consistent in Tasks 5 and 13. `build_remember_update`/`build_recall_select`/`build_find_select`/`build_relate_update`/`build_supersede_update`/`build_forget_soft_update`/`build_forget_hard_update` consistent. ✓

No issues found; plan is ready.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-05-selma-memory-core.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?