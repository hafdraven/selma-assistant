"""Typed memory API (spec §4)."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from pyoxigraph import BlankNode

from . import sparql
from .exceptions import ProvenanceError


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# SPARQL UPDATE verbs whose leading keyword means `ask` should dispatch to
# `backend.update` rather than `backend.query`.
_UPDATE_VERBS = ("INSERT", "DELETE", "LOAD", "CLEAR", "CREATE", "DROP",
                 "COPY", "MOVE", "ADD")


def _is_update(sparql_str: str) -> bool:
    stripped = sparql_str.lstrip()
    # skip a leading prologue / PREFIX declarations
    head = stripped
    while True:
        low = head.lower()
        if low.startswith("prefix"):
            head = head[head.find("\n") + 1:] if "\n" in head else ""
            continue
        if low.startswith("base"):
            head = head[head.find("\n") + 1:] if "\n" in head else ""
            continue
        break
    first = head.split(None, 1)[0].upper() if head.split(None, 1) else ""
    return first in _UPDATE_VERBS


class MemoryAPI:
    def __init__(self, backend) -> None:
        self._backend = backend

    # -- passthrough / describe --
    def ask(self, sparql_str: str, bindings: dict | None = None):
        """Passthrough SPARQL. Routes UPDATE/INSERT/DELETE verbs to
        `backend.update`; SELECT/CONSTRUCT/ASK to `backend.query`."""
        if _is_update(sparql_str):
            return self._backend.update(sparql_str, bindings=bindings)
        return self._backend.query(sparql_str, bindings=bindings)

    def describe(self):
        from .ontology import describe
        return describe()

    # -- writes --
    def remember(self, subject, predicate, obj, *, stated_by,
                 confidence=1.0, valid_from=None, valid_to=None, source=None):
        if stated_by is None:
            raise ProvenanceError("stated_by is required")
        if subject is None:
            subject = BlankNode(f"fact{secrets.token_hex(4)}")
        fact = BlankNode(f"fact{secrets.token_hex(4)}")
        update = sparql.build_remember_update(
            fact, subject, predicate, obj, stated_by=stated_by,
            confidence=confidence, valid_from=valid_from, valid_to=valid_to,
            source=source, now=_now_iso())
        self._backend.update(update)
        return subject

    def relate(self, subject, predicate, obj, *, stated_by,
               valid_from=None, valid_to=None):
        if stated_by is None:
            raise ProvenanceError("stated_by is required")
        fact = BlankNode(f"fact{secrets.token_hex(4)}")
        update = sparql.build_relate_update(
            fact, subject, predicate, obj, stated_by=stated_by,
            valid_from=valid_from, valid_to=valid_to, now=_now_iso())
        self._backend.update(update)
        return subject

    # -- reads --
    def recall(self, subject=None, predicate=None, obj=None, *,
               as_of=None, include_history=False) -> list[dict]:
        q = sparql.build_recall_select(subject, predicate, obj,
                                       as_of=as_of,
                                       include_history=include_history)
        out = []
        for row in self._backend.query(q):
            out.append({
                "s": row["s"], "p": row["p"], "o": row["o"],
                "g": None,
                "vf": row["vf"] if "vf" in row else None,
                "vt": row["vt"] if "vt" in row else None,
            })
        return out

    def find(self, class_uri: str, *, filters=None, as_of=None) -> list:
        q = sparql.build_find_select(class_uri, filters=filters, as_of=as_of)
        return [row["s"] for row in self._backend.query(q)]