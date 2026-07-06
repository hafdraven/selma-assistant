from selma.memory.api import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph


def test_ask_passthrough_runs_sparql(tmp_path):
    api = MemoryAPI(EmbeddedOxigraph(path=tmp_path / "s"))
    rows = list(api.ask("SELECT ?s ?p ?o WHERE { ?s ?p ?o }"))
    assert rows == []  # empty store