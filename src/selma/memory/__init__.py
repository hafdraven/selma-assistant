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