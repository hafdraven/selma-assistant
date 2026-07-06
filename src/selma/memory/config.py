"""Backend configuration (spec §3 selection)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class BackendConfig:
    kind: str = "embedded"
    path: Path | str | None = None