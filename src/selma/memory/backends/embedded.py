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
    statement typed API batches are issued as a single SPARQL UPDATE, so they
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