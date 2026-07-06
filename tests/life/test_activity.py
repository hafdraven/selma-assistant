"""Tests for ActivityService (spec §3, §4)."""
from __future__ import annotations

import pytest

from selma.life.exceptions import (ActivityAlreadyRunningError,
                                   ActivityNotRunningError)
from selma.memory import terms


def test_start_persists_activity(activities, fresh_api):
    u = activities.start("Writing", tags=["work", "deep"],
                         at="2026-07-06T09:00:00")
    found = fresh_api.find(terms.uri("Event"))
    assert u in [f.value for f in found]


def test_start_sets_label_and_tags(activities):
    u = activities.start("Writing", tags=["work", "deep"],
                         at="2026-07-06T09:00:00")
    a = activities.history()[0]
    assert a.label == "Writing"
    assert set(a.tags) == {"work", "deep"}


def test_current_returns_running(activities):
    u = activities.start("Writing", at="2026-07-06T09:00:00")
    cur = activities.current()
    assert cur is not None
    assert cur.uri == u
    assert cur.end is None


def test_current_none_when_stopped(activities):
    assert activities.current() is None
    u = activities.start("Writing", at="2026-07-06T09:00:00")
    activities.stop(u, at="2026-07-06T10:00:00")
    assert activities.current() is None


def test_stop_sets_end(activities):
    u = activities.start("Writing", at="2026-07-06T09:00:00")
    activities.stop(u, at="2026-07-06T10:00:00")
    a = activities.history()[0]
    assert a.end == "2026-07-06T10:00:00"


def test_stop_not_running_raises(activities):
    u = activities.start("Writing", at="2026-07-06T09:00:00")
    activities.stop(u, at="2026-07-06T10:00:00")
    with pytest.raises(ActivityNotRunningError):
        activities.stop(u, at="2026-07-06T11:00:00")


def test_start_while_running_raises(activities):
    activities.start("Writing", at="2026-07-06T09:00:00")
    with pytest.raises(ActivityAlreadyRunningError):
        activities.start("Reading", at="2026-07-06T09:30:00")


def test_history_filters_since_until(activities):
    a = activities.start("A", at="2026-07-06T09:00:00")
    activities.stop(a, at="2026-07-06T10:00:00")
    b = activities.start("B", at="2026-07-06T11:00:00")
    activities.stop(b, at="2026-07-06T12:00:00")
    since = activities.history(since="2026-07-06T10:30:00")
    assert [h.uri for h in since] == [b]
    until = activities.history(until="2026-07-06T10:30:00")
    assert [h.uri for h in until] == [a]


def test_history_filters_tags(activities):
    a = activities.start("A", tags=["work"], at="2026-07-06T09:00:00")
    activities.stop(a, at="2026-07-06T10:00:00")
    b = activities.start("B", tags=["play"], at="2026-07-06T11:00:00")
    activities.stop(b, at="2026-07-06T12:00:00")
    tagged = activities.history(tags=["play"])
    assert [h.uri for h in tagged] == [b]


def test_start_with_part_of(activities):
    u = activities.start("Task X", part_of="https://ex/project1",
                         at="2026-07-06T09:00:00")
    a = activities.history()[0]
    assert a.part_of == "https://ex/project1"