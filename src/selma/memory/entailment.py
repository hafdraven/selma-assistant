"""Light entailment support (spec §2): subclass, inverseOf, transitive.

Applied at query time by the SPARQL builders in sparql.py — no reasoner.
"""
from __future__ import annotations

from .ontology import CLASS_HIERARCHY, INVERSE_PROPS, TRANSITIVE_PROPS
from .terms import uri


def _children_map() -> dict[str, list[str]]:
    children: dict[str, list[str]] = {short: [] for short in CLASS_HIERARCHY}
    for child, parents in CLASS_HIERARCHY.items():
        for parent in parents:
            children[parent].append(child)
    return children


_CHILDREN = _children_map()


def subclass_expand(class_uri: str) -> list[str]:
    """Return [class_uri, *all_transitive_subclasses].

    DFS with the input class pushed first, so the input class is always
    the first element of the result. Deterministic order via the
    underlying CLASS_HIERARCHY / _CHILDREN insertion order.
    """
    short = class_uri.split("#")[-1]
    out: list[str] = []
    stack = [short]
    seen: set[str] = set()
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        out.append(uri(cur))
        # extend in reverse so left-most children are processed first,
        # keeping the traversal deterministic and stable.
        stack.extend(reversed(_CHILDREN.get(cur, [])))
    return out


def inverse_of(prop_uri: str) -> str | None:
    short = prop_uri.split("#")[-1]
    for a, b in INVERSE_PROPS:
        if short == a:
            return uri(b)
        if short == b:
            return uri(a)
    return None


def is_transitive(prop_uri: str) -> bool:
    return prop_uri.split("#")[-1] in TRANSITIVE_PROPS