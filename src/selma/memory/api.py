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