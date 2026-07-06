"""Remote triplestore backend stub (spec §3). To be implemented in a later sub-project."""
from __future__ import annotations


class RemoteTriplestore:
    def __init__(self, *, endpoint: str) -> None:
        raise NotImplementedError(
            "RemoteTriplestore backend is a stub; a later sub-project will implement it.")