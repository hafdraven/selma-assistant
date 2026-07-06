"""Parametrizes backend conformance tests across every implemented backend."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


def _backends():
    """Return (id, factory) pairs for every implemented backend."""
    impls = []
    try:
        from selma.memory.backends.embedded import EmbeddedOxigraph

        def make_embedded(tmp_path):
            return EmbeddedOxigraph(path=tmp_path / "store")

        impls.append(("embedded", make_embedded))
    except ImportError:
        pass
    try:
        from selma.memory.backends.remote import RemoteTriplestore

        impls.append(("remote", lambda tmp_path: RemoteTriplestore(endpoint="http://example/")))
    except ImportError:
        pass
    try:
        from selma.memory.backends.managed import ManagedRDF

        impls.append(("managed", lambda tmp_path: ManagedRDF(endpoint="http://example/")))
    except ImportError:
        pass
    return impls


def pytest_generate_tests(metafunc):
    if "backend_factory" in metafunc.fixturenames:
        impls = _backends()
        if not impls:
            pytest.skip("no backend implementations available")
        metafunc.parametrize("backend_factory", [f for _, f in impls], ids=[i for i, _ in impls])


@pytest.fixture
def backend(backend_factory, tmp_path):
    store = backend_factory(tmp_path)
    try:
        yield store
    finally:
        store.close()