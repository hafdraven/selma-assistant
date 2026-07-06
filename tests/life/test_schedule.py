"""Tests for ScheduleService (spec §3, §4)."""
from __future__ import annotations

import pytest

from selma.life.exceptions import ScheduleConflictError
from selma.life.models import ScheduleEvent
from selma.memory import terms


def test_create_persists_event(schedule, fresh_api):
    u = schedule.create("2026-07-06T09:00:00", "2026-07-06T10:00:00",
                        label="Standup")
    found = fresh_api.find(terms.uri("Event"))
    assert u in [f.value for f in found]


def test_get_returns_event(schedule):
    u = schedule.create("2026-07-06T09:00:00", "2026-07-06T10:00:00",
                        label="Standup",
                        part_of="https://ex/project1")
    ev = schedule.get(u)
    assert ev.start == "2026-07-06T09:00:00"
    assert ev.end == "2026-07-06T10:00:00"
    assert ev.label == "Standup"
    assert ev.part_of == "https://ex/project1"


def test_list_day(schedule):
    a = schedule.create("2026-07-06T09:00:00", "2026-07-06T10:00:00",
                        label="A")
    b = schedule.create("2026-07-06T14:00:00", "2026-07-06T15:00:00",
                        label="B")
    schedule.create("2026-07-07T09:00:00", "2026-07-07T10:00:00",
                    label="C")
    items = schedule.list(day="2026-07-06")
    uris = {e.uri for e in items}
    assert uris == {a, b}


def test_list_week(schedule):
    # 2026-07-06 is a Monday; the week is Mon 07-06 through Sun 07-12.
    a = schedule.create("2026-07-06T09:00:00", "2026-07-06T10:00:00",
                        label="Mon")
    b = schedule.create("2026-07-08T09:00:00", "2026-07-08T10:00:00",
                        label="Wed")
    c = schedule.create("2026-07-12T09:00:00", "2026-07-12T10:00:00",
                        label="Sun")
    schedule.create("2026-07-13T09:00:00", "2026-07-13T10:00:00",
                    label="NextMon")
    items = schedule.list(week="2026-07-06")
    uris = {e.uri for e in items}
    assert uris == {a, b, c}


def test_conflicts_detects_overlap(schedule):
    schedule.create("2026-07-06T09:00:00", "2026-07-06T10:00:00",
                    label="A")
    conflicts = schedule.conflicts("2026-07-06T09:30:00",
                                   "2026-07-06T10:30:00")
    assert len(conflicts) == 1


def test_conflicts_no_overlap(schedule):
    schedule.create("2026-07-06T09:00:00", "2026-07-06T10:00:00",
                    label="A")
    conflicts = schedule.conflicts("2026-07-06T10:00:00",
                                   "2026-07-06T11:00:00")
    assert conflicts == []


def test_conflicts_exclude(schedule):
    a = schedule.create("2026-07-06T09:00:00", "2026-07-06T10:00:00",
                        label="A")
    conflicts = schedule.conflicts("2026-07-06T09:30:00",
                                   "2026-07-06T10:30:00", exclude=a)
    assert conflicts == []


def test_create_overlapping_raises(schedule):
    schedule.create("2026-07-06T09:00:00", "2026-07-06T10:00:00",
                    label="A")
    with pytest.raises(ScheduleConflictError):
        schedule.create("2026-07-06T09:30:00", "2026-07-06T10:30:00",
                        label="B")


def test_move_changes_start(schedule):
    u = schedule.create("2026-07-06T09:00:00", "2026-07-06T10:00:00",
                        label="A")
    schedule.move(u, "2026-07-06T11:00:00")
    ev = schedule.get(u)
    assert ev.start == "2026-07-06T11:00:00"
    assert ev.end == "2026-07-06T12:00:00"


def test_move_with_new_end(schedule):
    u = schedule.create("2026-07-06T09:00:00", "2026-07-06T10:00:00",
                        label="A")
    schedule.move(u, "2026-07-06T11:00:00", new_end="2026-07-06T13:00:00")
    ev = schedule.get(u)
    assert ev.start == "2026-07-06T11:00:00"
    assert ev.end == "2026-07-06T13:00:00"


def test_move_conflict_raises(schedule):
    schedule.create("2026-07-06T11:00:00", "2026-07-06T12:00:00",
                    label="Blocker")
    u = schedule.create("2026-07-06T09:00:00", "2026-07-06T10:00:00",
                        label="A")
    with pytest.raises(ScheduleConflictError):
        schedule.move(u, "2026-07-06T11:30:00")


def test_cancel_removes_from_list(schedule):
    u = schedule.create("2026-07-06T09:00:00", "2026-07-06T10:00:00",
                        label="A")
    schedule.cancel(u)
    assert schedule.list(day="2026-07-06") == []