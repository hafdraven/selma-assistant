"""Typed memory API (spec §4)."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from pyoxigraph import BlankNode, Literal

from . import sparql
from .exceptions import ProvenanceError, QueryError, SupersedeError
from .terms import PROPS, uri


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

    # -- supersession --
    def supersede(self, fact_uri, new_value, *, stated_by, reason=None):
        """Mark the current fact(s) about `fact_uri` as superseded (set their
        reification node's `validTo = now`) and assert a fresh reified fact
        for `new_value`, inheriting the old fact's predicate and linking to
        the old fact's reification node via `selma:supersedes`.

        `fact_uri` is the data subject (e.g. `<http://ex/a>`), not the blank-
        node fact: the reification model attaches `validTo` to the blank-node
        `_:factNNN` that reifies the (subject, predicate, object) triple, so
        we join `?f rdf:subject <fact_uri>` to find the node to retire.

        Raises:
          ProvenanceError if `stated_by` is None.
          SupersedeError if `fact_uri`'s reification node already has a
            `validTo` (already superseded).
        """
        if stated_by is None:
            raise ProvenanceError("stated_by is required")

        fact_s = sparql.serialize_term(fact_uri)
        prologue = sparql._prologue()

        # 1. Refuse if the old fact already has a validTo (already superseded).
        check = (f"{prologue}\nSELECT ?vt WHERE {{ "
                 f"?f <{sparql.RDF_SUBJECT}> {fact_s} ; "
                 f"<{PROPS['validTo']}> ?vt }}")
        if list(self._backend.query(check)):
            raise SupersedeError(
                f"{fact_uri} already has a validTo (already superseded)")

        # 2. Find the old fact's predicate (inherited by the new fact).
        pred_q = (f"{prologue}\nSELECT ?p WHERE {{ "
                  f"?f <{sparql.RDF_SUBJECT}> {fact_s} ; "
                  f"<{sparql.RDF_PREDICATE}> ?p }}")
        rows = list(self._backend.query(pred_q))
        predicate = rows[0]["p"]

        # 3. Find the old fact's reification node so the new fact can link to
        #    it via selma:supersedes.
        node_q = (f"{prologue}\nSELECT ?f WHERE {{ "
                  f"?f <{sparql.RDF_SUBJECT}> {fact_s} ; "
                  f"<{sparql.RDF_PREDICATE}> {sparql.serialize_term(predicate)} }}")
        old_node = list(self._backend.query(node_q))[0]["f"]

        now = _now_iso()

        # 4. Set validTo = now on the old fact's reification node.
        retire = (
            f"{prologue}\n"
            f"DELETE {{ ?f <{PROPS['validTo']}> ?vt }} "
            f"INSERT {{ ?f <{PROPS['validTo']}> {sparql._dt(now)} }} "
            f"WHERE {{ ?f <{sparql.RDF_SUBJECT}> {fact_s} . "
            f"OPTIONAL {{ ?f <{PROPS['validTo']}> ?vt }} }}"
        )
        self._backend.update(retire)

        # 5. Insert a fresh reified fact for new_value, inheriting the old
        #    predicate and linking to the old fact node via supersedes.
        new_fact = BlankNode(f"fact{secrets.token_hex(4)}")
        # Build the reification clauses, then append the supersedes link in
        # the same INSERT DATA block (a blank node cannot be shared across
        # multiple INSERT DATA blocks in SPARQL).
        clauses = sparql._fact_clauses(
            new_fact, fact_uri, predicate, new_value,
            stated_by=stated_by, confidence=None, valid_from=None,
            valid_to=None, source=reason if reason is not None else None,
            now=now)
        # _fact_clauses returns ["INSERT DATA { ... }"]; splice the
        # supersedes triple inside the closing brace.
        supersedes_triple = (
            f"{sparql.serialize_term(new_fact)} "
            f"<{PROPS['supersedes']}> {sparql.serialize_term(old_node)}"
        )
        # Replace the trailing " }" with " . <supersedes> }".
        first_clause = clauses[0]
        assert first_clause.endswith(" }")
        clauses[0] = first_clause[:-2] + " . " + supersedes_triple + " }"
        new_update = sparql._prologue() + "\n" + ";\n".join(clauses) + "\n"
        self._backend.update(new_update)
        return new_fact

    # -- forgetting --
    def forget(self, subject=None, predicate=None, obj=None, *,
               soft=True, reason=None) -> int:
        """Retire (soft) or physically remove (hard) reified facts matching
        the (subject, predicate, obj) filter.

        Soft delete: set `validTo = now` on matching facts' reification nodes
        so they drop out of current `recall` but remain in history.
        Hard delete: log the removed facts to the `selma:audit` named graph
        then physically remove their reification quads.

        Raises:
          QueryError if all of subject/predicate/obj are None (spec §4 guard
            against wiping the store).
          ProvenanceError if `soft=False` and `reason` is None (hard delete
            requires a reason).
        Returns the count of affected facts.
        """
        if subject is None and predicate is None and obj is None:
            raise QueryError(
                "forget requires at least one of subject/predicate/obj")
        if not soft and reason is None:
            raise ProvenanceError("hard forget requires a reason")

        prologue = sparql._prologue()
        now = _now_iso()
        audit_graph = uri("audit")

        # Build the reification triple-pattern with concrete terms where
        # given, variables where not. We bind ?f (the fact node) and ?s/?p/?o
        # (the reified data terms) so the soft-update WHERE can reuse them
        # and the count matches the same set.
        subj_t = sparql.serialize_term(subject) if subject is not None else "?s"
        pred_t = sparql.serialize_term(predicate) if predicate is not None else "?p"
        obj_t = sparql.serialize_term(obj) if obj is not None else "?o"

        # Reification match: ?f rdf:subject/predicate/object (s/p/o).
        match_body = (
            f"?f <{sparql.RDF_SUBJECT}> {subj_t} ; "
            f"<{sparql.RDF_PREDICATE}> {pred_t} ; "
            f"<{sparql.RDF_OBJECT}> {obj_t}"
        )

        # Count matching reification nodes.
        count_q = (f"{prologue}\nSELECT (COUNT(*) AS ?n) WHERE {{ {match_body} }}")
        n = int(list(self._backend.query(count_q))[0]["n"].value)

        if soft:
            # Set validTo = now on matching reification nodes. The default-
            # recall filter (!BOUND(?vt)) drops these from the current view
            # while history (include_history=True) still retains the full
            # validFrom..validTo window. validFrom is left intact so the
            # historical record is complete.
            upd = (
                f"{prologue}\n"
                f"DELETE {{ ?f <{PROPS['validTo']}> ?vt }} "
                f"INSERT {{ ?f <{PROPS['validTo']}> {sparql._dt(now)} }} "
                f"WHERE {{ {match_body} . "
                f"OPTIONAL {{ ?f <{PROPS['validTo']}> ?vt }} }}"
            )
            self._backend.update(upd)
            return n

        # Hard delete: audit then physically remove.
        reason_lit = sparql.serialize_term(Literal(reason))

        # Log one audit entry per matching fact to the audit named graph.
        # BNODE() is bound in WHERE so the INSERT template has a fresh blank
        # node per matching fact (oxigraph does not auto-generate blank nodes
        # that appear only in the INSERT template).
        audit = (
            f"{prologue}\n"
            f"INSERT {{ GRAPH <{audit_graph}> {{ "
            f"?a <{sparql.RDF_TYPE}> <{uri('AuditEntry')}> ; "
            f"<{PROPS['recordedAt']}> {sparql._dt(now)} ; "
            f"<{PROPS['source']}> {reason_lit} ; "
            f"<{sparql.RDF_SUBJECT}> {subj_t} ; "
            f"<{sparql.RDF_PREDICATE}> {pred_t} ; "
            f"<{sparql.RDF_OBJECT}> {obj_t} }} }} "
            f"WHERE {{ BIND(BNODE() AS ?a) . {match_body} }}"
        )
        self._backend.update(audit)

        # Physically remove every quad that mentions a matching fact node
        # (?f ?mp ?mo), plus the reified data triple when s/p/o are all bound
        # concretely; when any of s/p/o is a variable we delete only the
        # reification quads to avoid dropping unrelated data triples.
        if subject is not None and predicate is not None and obj is not None:
            delete_triple = (
                f"{sparql.serialize_term(subject)} "
                f"{sparql.serialize_term(predicate)} "
                f"{sparql.serialize_term(obj)} . "
            )
        else:
            delete_triple = ""

        delete = (
            f"{prologue}\n"
            f"DELETE WHERE {{ {match_body} . "
            f"?f ?mp ?mo . {delete_triple}}}"
        )
        self._backend.update(delete)
        return n