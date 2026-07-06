"""SPARQL query/update builders. Pure functions — no store access (spec §4)."""
from __future__ import annotations

from pyoxigraph import BlankNode, Literal, NamedNode

from .terms import PREFIXES, PROPS, XSD

XSD_DT = XSD["dateTime"]
XSD_DECIMAL = XSD["decimal"]


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


def build_remember_update(s, p, o, ctx, *, stated_by, confidence,
                          valid_from, valid_to, source, now) -> str:
    """INSERT a Fact quad plus its temporal/provenance metadata quads.

    `s`, `p`, `o`, `ctx`, `stated_by` are pyoxigraph terms (or None for the
    optional ones). `confidence` is a numeric (or None) emitted as
    xsd:decimal. `source` is a pyoxigraph term or a plain string (emitted as
    a plain literal) or None. `now`, `valid_from`, `valid_to` are ISO
    datetime strings (or None for the optional ones).
    """
    g = serialize_term(ctx)
    subj = serialize_term(s)
    pred = serialize_term(p)
    obj = serialize_term(o)
    clauses = [
        f"INSERT DATA {{ GRAPH {g} {{ {subj} {pred} {obj} }}}}",
        f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['recordedAt']}> {_dt(now)} }}}}",
        f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['statedBy']}> {serialize_term(stated_by)} }}}}",
    ]
    if confidence is not None:
        clauses.append(
            f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['confidence']}> "
            f'"{confidence}"^^<{XSD_DECIMAL}> }}}}')
    if valid_from is not None:
        clauses.append(
            f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['validFrom']}> {_dt(valid_from)} }}}}")
    if valid_to is not None:
        clauses.append(
            f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['validTo']}> {_dt(valid_to)} }}}}")
    if source is not None:
        if isinstance(source, str):
            src = serialize_term(Literal(source))
        else:
            src = serialize_term(source)
        clauses.append(
            f"INSERT DATA {{ GRAPH {g} {{ {subj} <{PROPS['source']}> {src} }}}}")
    return _prologue() + "\n" + ";\n".join(clauses) + "\n"


def build_recall_select(s, p, o, *, as_of, include_history) -> str:
    """SELECT quads matching (s,p,o) across all named graphs, filtered by
    validity window.

    - include_history=True: no validity filter (all matching rows).
    - include_history=False, as_of given: keep facts where validFrom is
      unbound OR validFrom <= as_of, and validTo is unbound OR
      validTo >= as_of.
    - include_history=False, as_of None: exclude only facts with a past
      validTo (superseded/expired); facts without a validTo are kept.
    """
    conds = []
    if s is not None:
        conds.append(f"?s = {serialize_term(s)}")
    if p is not None:
        conds.append(f"?p = {serialize_term(p)}")
    if o is not None:
        conds.append(f"?o = {serialize_term(o)}")

    body = (
        f"GRAPH ?g {{ ?s ?p ?o . "
        f"OPTIONAL {{ ?s <{PROPS['validFrom']}> ?vf }} . "
        f"OPTIONAL {{ ?s <{PROPS['validTo']}> ?vt }} }}"
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
        # Exclude only facts whose validTo is in the past.
        filt = (
            "FILTER(NOT EXISTS { ?s <" + PROPS['validTo'] + "> ?vt . "
            "FILTER(?vt < " + _dt("1970-01-01T00:00:00") + ") })"
        )
        if conds:
            filt = "FILTER(" + " && ".join(conds) + ") " + filt

    where_body = f"{{ {body}"
    if filt:
        where_body += f" {filt}"
    where_body += " }"
    return f"{_prologue()}\nSELECT ?s ?p ?o ?g ?vf ?vt WHERE {where_body}"