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