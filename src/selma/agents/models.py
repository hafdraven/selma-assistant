"""Plain data classes for agents entities (spec §3).

Frozen dataclasses. Row mappings convert pyoxigraph query terms into Python
values: ``None`` for unbound optionals, ``Literal.value`` / ``NamedNode.value``
otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass


def _val(term) -> str | None:
    """Extract a Python value from a pyoxigraph term (or None)."""
    if term is None:
        return None
    return term.value


def _row_get(row, key: str):
    """Read an optional column from a QuerySolution (returns None if unbound)."""
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


@dataclass(frozen=True)
class Project:
    """A ``selma:Project`` with label, description, optional partOf."""

    uri: str
    label: str | None = None
    description: str | None = None
    part_of: str | None = None

    @classmethod
    def from_row(cls, row) -> "Project":
        return cls(
            uri=_val(_row_get(row, "uri")),
            label=_val(_row_get(row, "label")),
            description=_val(_row_get(row, "desc")),
            part_of=_val(_row_get(row, "part")),
        )


@dataclass(frozen=True)
class Task:
    """A ``selma:Task`` with lifecycle and coordination properties."""

    uri: str
    label: str | None = None
    description: str | None = None
    status: str | None = None
    owned_by: str | None = None
    due_by: str | None = None
    completed_at: str | None = None
    part_of: str | None = None
    block_reason: str | None = None
    execution_result: str | None = None

    @classmethod
    def from_row(cls, row) -> "Task":
        return cls(
            uri=_val(_row_get(row, "uri")),
            label=_val(_row_get(row, "label")),
            description=_val(_row_get(row, "desc")),
            status=_val(_row_get(row, "status")),
            owned_by=_val(_row_get(row, "owner")),
            due_by=_val(_row_get(row, "due")),
            completed_at=_val(_row_get(row, "completed")),
            part_of=_val(_row_get(row, "part")),
            block_reason=_val(_row_get(row, "blockreason")),
            execution_result=_val(_row_get(row, "execresult")),
        )