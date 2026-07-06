"""Storage backends for selma.memory."""
from __future__ import annotations

from ..config import BackendConfig
from .embedded import EmbeddedOxigraph
from .protocol import Backend


def get_backend(config: "BackendConfig") -> Backend:
    """Return a backend instance per the config (spec §3 selection)."""
    if config.kind == "embedded":
        return EmbeddedOxigraph(path=config.path)
    raise NotImplementedError(f"backend kind {config.kind!r} not implemented yet")


__all__ = ["Backend", "EmbeddedOxigraph", "get_backend"]