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