"""Plain data classes for life entities (spec §3).

Row mappings convert pyoxigraph query terms into Python values. A ``None``
value (an unbound optional) becomes ``None``; a ``Literal`` becomes its
lexical ``.value``; a ``NamedNode`` becomes its ``.value`` URI string.

pyoxigraph ``QuerySolution`` does not support ``.get()``, and ``in`` checks
by value rather than key, so optional columns are accessed directly with
``row[key]`` which returns ``None`` when the variable is unbound.
"""
from __future__ import annotations

from dataclasses import dataclass, field


def _val(term) -> str | None:
    """Extract a Python value from a pyoxigraph term (or None)."""
    if term is None:
        return None
    return term.value


def _row_get(row, key: str):
    """Read an optional column from a QuerySolution.

    Direct indexing returns ``None`` for unbound variables; missing keys
    raise, so callers must only ask for keys the query actually projects.
    """
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


@dataclass
class Reminder:
    """A ``selma:Reminder`` with fire time, optional label and target."""

    uri: str
    fire_at: str
    label: str | None = None
    about: str | None = None
    fired_at: str | None = None

    @classmethod
    def from_row(cls, row) -> "Reminder":
        return cls(
            uri=_val(_row_get(row, "r")),
            fire_at=_val(row["vf"]),
            label=_val(_row_get(row, "label")),
            about=_val(_row_get(row, "about")),
            fired_at=_val(_row_get(row, "fired")),
        )


@dataclass
class ScheduleEvent:
    """A scheduled ``selma:Event`` with start, end, optional label and parent."""

    uri: str
    start: str
    end: str | None = None
    label: str | None = None
    part_of: str | None = None

    @classmethod
    def from_row(cls, row) -> "ScheduleEvent":
        return cls(
            uri=_val(_row_get(row, "uri")),
            start=_val(row["start"]),
            end=_val(_row_get(row, "end")),
            label=_val(_row_get(row, "label")),
            part_of=_val(_row_get(row, "part")),
        )


@dataclass
class Activity:
    """An activity ``selma:Event`` with start, optional end, label, tags."""

    uri: str
    start: str
    end: str | None = None
    label: str | None = None
    tags: list[str] = field(default_factory=list)
    part_of: str | None = None

    @classmethod
    def from_row(cls, row) -> "Activity":
        return cls(
            uri=_val(_row_get(row, "uri")),
            start=_val(row["start"]),
            end=_val(_row_get(row, "end")),
            label=_val(_row_get(row, "label")),
            part_of=_val(_row_get(row, "part")),
        )