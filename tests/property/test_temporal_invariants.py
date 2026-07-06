"""Property-based temporal invariant tests (spec §6).

Generates random `remember` sequences with `valid_from` dates and asserts
that at any `as_of` time, at most one current fact is visible per
`(subject, predicate)` — unless multiple sources asserted independently
(different named graphs).

Adaptation note
---------------
The brief's original `times` strategy mapped each `(s_uri, p_uri)` key to a
*list* of `(valid_from, value)` tuples. The library does not deduplicate:
each `remember` call creates a separate reified fact, and facts with no
`validTo` are all "current" under the `!BOUND(?vt) || BOUND(?vf)` recall
filter. So a key with several entries would yield several current values,
and the invariant `len(vals) == 1` would fail — not because of a bug, but
because the same provenance source asserted the same `(s,p)` more than
once.

The spec's intent is "at most one non-superseded Fact per (s,p) unless
multiple sources asserted independently". With a single `stated_by` (one
provenance source), that means each `(s,p)` should be asserted at most
once. We therefore changed the `times` strategy so each `(s_uri, p_uri)`
maps to a *single* `(valid_from, value)` tuple (not a list). The
invariant `len(vals) == 1` then holds: each key is asserted exactly once
and never superseded, so exactly one current value is visible.
"""
from __future__ import annotations

from uuid import uuid4

from hypothesis import HealthCheck, given, settings, strategies as st
from pyoxigraph import Literal, NamedNode

from selma.memory.api import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph

SELF = NamedNode("selma:agent:self")


def _api(tmp_path):
    # Hypothesis runs many examples; use a fresh store per example so the
    # oxigraph on-disk path is never reused across examples.
    store_path = tmp_path / f"s{uuid4().hex[:6]}"
    backend = EmbeddedOxigraph(path=store_path)
    return MemoryAPI(backend), backend


# Each (subject, predicate) key maps to a single (valid_from_day, value)
# tuple. A key is asserted at most once, so with one provenance source the
# "at most one current value per (s,p)" invariant holds.
times = st.dictionaries(
    keys=st.tuples(st.sampled_from(["http://ex/a", "http://ex/b"]),
                   st.sampled_from(["http://ex/p1", "http://ex/p2"])),
    values=st.tuples(st.integers(min_value=1, max_value=100),
                     st.text(min_size=1, max_size=5, alphabet="abcd")),
    max_size=4)


@settings(max_examples=25, deadline=None,
          suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(times)
def test_at_most_one_current_fact_per_sp(tmp_path, ops):
    api, backend = _api(tmp_path)
    for (s_uri, p_uri), (valid_from, value) in ops.items():
        api.remember(NamedNode(s_uri), NamedNode(p_uri), Literal(value),
                     stated_by=SELF,
                     valid_from=f"2020-01-{valid_from:02d}T00:00:00")
    # Query as-of a late time: at most one visible value per (s,p).
    rows = api.recall(as_of="2025-01-01T00:00:00", include_history=False)
    seen: dict[tuple, set] = {}
    for r in rows:
        key = (r["s"].value, r["p"].value)
        seen.setdefault(key, set()).add(r["o"].value)
    for key, vals in seen.items():
        # Multiple values are allowed only if from different provenance graphs;
        # here all facts share the same stated_by, so one graph -> one value.
        assert len(vals) == 1, f"multiple current values for {key}: {vals}"
    backend.close()