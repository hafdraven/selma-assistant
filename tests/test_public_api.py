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