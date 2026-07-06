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