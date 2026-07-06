"""Shared pytest fixtures for selma.memory tests."""
from __future__ import annotations

import pytest


@pytest.fixture
def fresh_api(tmp_path):
    """A MemoryAPI over a fresh embedded backend. Wired in Task 8."""
    pytest.skip("MemoryAPI not implemented yet")