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