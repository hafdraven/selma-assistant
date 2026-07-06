"""Tests for ReminderService (spec §3, §6)."""
from __future__ import annotations

import threading
import time

import pytest
from pyoxigraph import NamedNode

from selma.life.exceptions import (ReminderNotFoundError, ReminderNotDueError,
                                   ReminderSchedulerError)
from selma.life.models import Reminder
from selma.memory import terms


def test_create_persists_reminder(reminders, fresh_api):
    u = reminders.create("2026-07-06T09:00:00", label="Standup",
                         about="https://ex/standup")
    # Type assertion is in the named graph, so find() discovers it.
    found = fresh_api.find(terms.uri("Reminder"))
    uris = [f.value for f in found]
    assert u in uris


def test_create_stores_label_and_about(reminders):
    u = reminders.create("2026-07-06T09:00:00", label="Standup",
                         about="https://ex/standup")
    r = reminders.get(u)
    assert r.fire_at == "2026-07-06T09:00:00"
    assert r.label == "Standup"
    assert r.about == "https://ex/standup"


def test_get_unknown_raises(reminders):
    with pytest.raises(ReminderNotFoundError):
        reminders.get("https://selma.example/ns/life#reminder/nope")


def test_list_returns_reminders(reminders):
    a = reminders.create("2026-07-06T09:00:00", label="A")
    b = reminders.create("2026-07-06T10:00:00", label="B")
    items = reminders.list()
    uris = {r.uri for r in items}
    assert {a, b} == uris


def test_list_excludes_fired_by_default(reminders):
    u = reminders.create("2026-07-06T09:00:00", label="A")
    reminders.fire(u, now="2026-07-06T09:00:00")
    assert reminders.list() == []
    # include_fired brings it back.
    fired = reminders.list(include_fired=True)
    assert len(fired) == 1
    assert fired[0].fired_at is not None


def test_list_due_before_filters(reminders):
    a = reminders.create("2026-07-06T09:00:00", label="A")
    reminders.create("2026-07-06T12:00:00", label="B")
    due = reminders.list(due_before="2026-07-06T10:00:00")
    assert [r.uri for r in due] == [a]


def test_fire_sets_fired_at(reminders):
    u = reminders.create("2026-07-06T09:00:00", label="A")
    reminders.fire(u, now="2026-07-06T09:00:00")
    r = reminders.get(u)
    assert r.fired_at == "2026-07-06T09:00:00"


def test_fire_future_raises_not_due(reminders):
    u = reminders.create("2026-07-06T09:00:00", label="A")
    with pytest.raises(ReminderNotDueError):
        reminders.fire(u, now="2026-07-06T08:00:00")


def test_fire_unknown_raises(reminders):
    with pytest.raises(ReminderNotFoundError):
        reminders.fire("https://selma.example/ns/life#reminder/nope",
                       now="2026-07-06T09:00:00")


def test_fire_is_idempotent(reminders):
    u = reminders.create("2026-07-06T09:00:00", label="A")
    reminders.fire(u, now="2026-07-06T09:00:00")
    reminders.fire(u, now="2026-07-06T09:30:00")  # no error
    r = reminders.get(u)
    # First fire time is preserved.
    assert r.fired_at == "2026-07-06T09:00:00"


def test_check_due_returns_unfired_due(reminders):
    a = reminders.create("2026-07-06T09:00:00", label="A")
    b = reminders.create("2026-07-06T11:00:00", label="B")
    due = reminders.check_due(now="2026-07-06T10:00:00")
    assert a in due
    assert b not in due


def test_check_due_marks_fired(reminders):
    a = reminders.create("2026-07-06T09:00:00", label="A")
    reminders.check_due(now="2026-07-06T10:00:00")
    r = reminders.get(a)
    assert r.fired_at == "2026-07-06T10:00:00"


def test_check_due_idempotent(reminders):
    a = reminders.create("2026-07-06T09:00:00", label="A")
    first = reminders.check_due(now="2026-07-06T10:00:00")
    second = reminders.check_due(now="2026-07-06T10:30:00")
    assert first == [a]
    assert second == []


def test_scheduler_fires_callback(reminders, fresh_api):
    u = reminders.create("2026-01-01T00:00:00", label="Past")
    fired: list[str] = []
    ev = threading.Event()

    def cb(ruri):
        fired.append(ruri)
        ev.set()

    reminders.start(cb, interval=0.05)
    try:
        assert ev.wait(timeout=5.0)
    finally:
        reminders.stop()
    assert u in fired


def test_start_while_running_raises(reminders):
    reminders.start(lambda _u: None, interval=10.0)
    try:
        with pytest.raises(ReminderSchedulerError):
            reminders.start(lambda _u: None, interval=10.0)
    finally:
        reminders.stop()


def test_stop_without_start_is_noop(reminders):
    reminders.stop()  # no error


def test_create_about_as_namednode(reminders):
    about = NamedNode("https://ex/task1")
    u = reminders.create("2026-07-06T09:00:00", about=about)
    r = reminders.get(u)
    assert r.about == "https://ex/task1"