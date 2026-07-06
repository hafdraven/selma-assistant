"""SPARQL query/update builders. Pure functions — no store access (spec §4)."""
from __future__ import annotations

from pyoxigraph import BlankNode, Literal, NamedNode

from .terms import CLASSES, PREFIXES, PROPS, XSD

XSD_DT = XSD["dateTime"]
XSD_DECIMAL = XSD["decimal"]

# RDF reification vocabulary (used to attach per-fact metadata to a specific
# s p o triple without conflating metadata across facts that share a subject).
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDF_SUBJECT = "http://www.w3.org/1999/02/22-rdf-syntax-ns#subject"
RDF_PREDICATE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#predicate"
RDF_OBJECT = "http://www.w3.org/1999/02/22-rdf-syntax-ns#object"


def serialize_term(t) -> str:
    """Turn a pyoxigraph term into SPARQL syntax.

    - NamedNode(v) -> <v>
    - BlankNode(id) -> _:id
    - Literal(v) -> "v" (with \\ and " escaped)
    - Literal(v, language="en") -> "v"@en
    - Literal(v, datatype=NamedNode(...)) -> "v"^^<datatype IRI>
    """
    if isinstance(t, NamedNode):
        return f"<{t.value}>"
    if isinstance(t, BlankNode):
        return f"_:{t.value}"
    if isinstance(t, Literal):
        lex = t.value.replace("\\", "\\\\").replace('"', '\\"')
        if t.language:
            return f'"{lex}"@{t.language}'
        if t.datatype is not None and t.datatype.value != XSD["string"]:
            return f'"{lex}"^^<{t.datatype.value}>'
        return f'"{lex}"'
    raise TypeError(f"cannot serialize {type(t)}")


def _dt(value) -> str:
    """Serialize an ISO datetime string as an xsd:dateTime literal."""
    return f'"{value}"^^<{XSD_DT}>'


def _prologue() -> str:
    return "\n".join(f"PREFIX {k}: <{v}>" for k, v in PREFIXES.items())


def _fact_clauses(fact, s, p, o, *, stated_by, confidence, valid_from,
                  valid_to, source, now) -> list[str]:
    """Build the INSERT DATA clauses for a reified fact.

    The fact node carries rdf:type selma:Fact, the reification of the s p o
    triple (rdf:subject/predicate/object), and the temporal/provenance
    metadata. Everything is stored in the default graph so that metadata
    (e.g. confidence) is queryable by plain SELECTs, while the reification
    join in build_recall_select keeps per-fact validity windows distinct
    even when several facts share the same subject.
    """
    f = serialize_term(fact)
    subj = serialize_term(s)
    pred = serialize_term(p)
    obj = serialize_term(o)
    triples = [
        f"{f} <{RDF_TYPE}> <{CLASSES['Fact']}>",
        f"{f} <{RDF_SUBJECT}> {subj}",
        f"{f} <{RDF_PREDICATE}> {pred}",
        f"{f} <{RDF_OBJECT}> {obj}",
        f"{subj} {pred} {obj}",
        f"{f} <{PROPS['recordedAt']}> {_dt(now)}",
        f"{f} <{PROPS['statedBy']}> {serialize_term(stated_by)}",
    ]
    if confidence is not None:
        triples.append(
            f"{f} <{PROPS['confidence']}> "
            f'"{confidence}"^^<{XSD_DECIMAL}>')
    if valid_from is not None:
        triples.append(
            f"{f} <{PROPS['validFrom']}> {_dt(valid_from)}")
    if valid_to is not None:
        triples.append(
            f"{f} <{PROPS['validTo']}> {_dt(valid_to)}")
    if source is not None:
        if isinstance(source, str):
            src = serialize_term(Literal(source))
        else:
            src = serialize_term(source)
        triples.append(
            f"{f} <{PROPS['source']}> {src}")
    return [f"INSERT DATA {{ {' . '.join(triples)} }}"]


def build_remember_update(fact, s, p, o, *, stated_by, confidence,
                          valid_from, valid_to, source, now) -> str:
    """INSERT a reified Fact plus its temporal/provenance metadata.

    `fact` is the blank-node fact subject that carries the metadata and
    reification of the (s, p, o) triple. The reified fact is stored in the
    default graph so metadata is queryable by plain SELECTs and per-fact
    validity windows do not conflate across facts sharing a subject. The
    remaining arguments are as in the Task 8 signature.
    """
    clauses = _fact_clauses(fact, s, p, o, stated_by=stated_by,
                           confidence=confidence, valid_from=valid_from,
                           valid_to=valid_to, source=source, now=now)
    return _prologue() + "\n" + ";\n".join(clauses) + "\n"


def build_recall_select(s, p, o, *, as_of, include_history) -> str:
    """SELECT (s,p,o,vf,vt) for fact triples matching (s,p,o), filtered by
    validity window.

    The triple pattern `?s ?p ?o` is joined (non-optionally) to its
    reified fact node via rdf:subject/predicate/object, which:

      - returns only triples that are actual asserted facts (metadata and
        reification quads have no reification of their own, so they drop
        out), and
      - gives each fact its own validFrom/validTo, so two facts sharing a
        subject do not conflate their validity windows.

    Validity filtering:
      - include_history=True: no validity filter (all matching rows).
      - include_history=False, as_of given: keep facts where validFrom is
        unbound OR validFrom <= as_of, and validTo is unbound OR
        validTo >= as_of.
      - include_history=False, as_of None: keep facts that are still current.
        A fact with a bounded validTo but no validFrom is a superseded/
        tombstoned marker (an end with no start) and is dropped; a fact
        with no validTo, or with a complete validFrom..validTo window, is
        kept.
    """
    conds = []
    if s is not None:
        conds.append(f"?s = {serialize_term(s)}")
    if p is not None:
        conds.append(f"?p = {serialize_term(p)}")
    if o is not None:
        conds.append(f"?o = {serialize_term(o)}")

    body = (
        f"?s ?p ?o . "
        f"?f <{RDF_SUBJECT}> ?s ; <{RDF_PREDICATE}> ?p ; <{RDF_OBJECT}> ?o . "
        f"OPTIONAL {{ ?f <{PROPS['validFrom']}> ?vf }} . "
        f"OPTIONAL {{ ?f <{PROPS['validTo']}> ?vt }}"
    )

    if include_history:
        filt = ""
    elif as_of is not None:
        conds.append(
            f"(!BOUND(?vf) || ?vf <= {_dt(as_of)}) && "
            f"(!BOUND(?vt) || ?vt >= {_dt(as_of)})"
        )
        filt = "FILTER(" + " && ".join(conds) + ")" if conds else ""
    else:
        # Drop only superseded markers: a validTo with no validFrom start
        # (validFrom unbound). Facts with an unbounded validTo, or with a
        # complete validFrom..validTo window, are kept.
        conds.append("!BOUND(?vt) || BOUND(?vf)")
        filt = "FILTER(" + " && ".join(conds) + ")" if conds else ""

    where_body = f"{{ {body}"
    if filt:
        where_body += f" {filt}"
    where_body += " }"
    return f"{_prologue()}\nSELECT ?s ?p ?o ?vf ?vt WHERE {where_body}"


def build_find_select(class_uri: str, *, filters, as_of) -> str:
    """SELECT DISTINCT ?s WHERE { ?s rdf:type ?type } for ?type in the
    subclass closure of `class_uri`.

    Subclass expansion is done in Python (subclass_expand) and emitted as
    a UNION so the store doesn't need a reasoner. Instance type triples are
    matched inside `GRAPH ?g { ... }` so that instances inserted into named
    graphs (e.g. via raw INSERT DATA) are found.

    When `as_of` is given, the type match is joined (optionally) to each
    subject's reified facts in the default graph and filtered to keep only
    instances that have a fact whose validFrom/validTo window includes
    `as_of`. Subjects with no reified facts (no metadata at all) are kept
    unchanged — `!BOUND(?vf)` admits them — so `as_of` never silently drops
    freshly inserted type-only instances.
    """
    from . import terms
    from .entailment import subclass_expand
    types = subclass_expand(class_uri)
    type_clauses = " UNION ".join(
        f"{{ GRAPH ?g {{ ?s a {serialize_term(NamedNode(t))} }}}}" for t in types)
    if filters:
        extra = " . ".join(
            f"?s <{terms.PROPS.get(k, k)}> {serialize_term(v)}"
            for k, v in filters.items())
        type_clauses = "{" + type_clauses + " . " + extra + "}"

    where_body = type_clauses
    filt = ""
    if as_of is not None:
        as_of_dt = _dt(as_of)
        # Join each ?s to any reified fact about it in the default graph and
        # keep only ?s whose (best) fact validity window includes as_of.
        where_body = (
            "{ " + type_clauses + " } "
            f"OPTIONAL {{ ?f <{RDF_SUBJECT}> ?s ; "
            f"<{RDF_PREDICATE}> ?p ; <{RDF_OBJECT}> ?o . "
            f"?f <{PROPS['validFrom']}> ?vf . "
            f"OPTIONAL {{ ?f <{PROPS['validTo']}> ?vt }} }} "
            f"FILTER((!BOUND(?vf) || ?vf <= {as_of_dt}) && "
            f"(!BOUND(?vt) || ?vt >= {as_of_dt}))"
        )
        # DISTINCT collapses duplicate ?s produced by multiple matching facts.
        # Wrap so the OPTIONAL+FILTER apply across the UNION of type clauses.
        where_body = "{ " + where_body + " }"
    return f"{_prologue()}\nSELECT DISTINCT ?s WHERE {{ {where_body} }}"


def build_relate_update(fact, s, p, o, *, stated_by, valid_from,
                        valid_to, now) -> str:
    """INSERT a reified Relationship assertion plus its temporal/provenance
    metadata. Structurally similar to build_remember_update but without
    confidence/source.
    """
    clauses = _fact_clauses(fact, s, p, o, stated_by=stated_by,
                           confidence=None, valid_from=valid_from,
                           valid_to=valid_to, source=None, now=now)
    return _prologue() + "\n" + ";\n".join(clauses) + "\n"