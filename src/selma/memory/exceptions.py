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