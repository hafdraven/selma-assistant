"""Tests for the LifeAssistant facade (spec §4)."""
from __future__ import annotations

from pyoxigraph import NamedNode

from selma.life import LifeAssistant
from selma.life.activity import ActivityService
from selma.life.reminders import ReminderService
from selma.life.schedule import ScheduleService
from selma.life.terms import default_stated_by


def test_facade_exposes_services(fresh_api):
    asst = LifeAssistant(fresh_api)
    assert isinstance(asst.reminders, ReminderService)
    assert isinstance(asst.schedule, ScheduleService)
    assert isinstance(asst.activities, ActivityService)


def test_facade_default_stated_by(fresh_api):
    asst = LifeAssistant(fresh_api)
    u = asst.reminders.create("2026-07-06T09:00:00", label="A")
    assert u.startswith("https://selma.example/ns/life#reminder/")


def test_facade_explicit_stated_by(fresh_api):
    agent = NamedNode("https://ex/me")
    asst = LifeAssistant(fresh_api, stated_by=agent)
    # Should not raise: stated_by flows through to remember().
    asst.schedule.create("2026-07-06T09:00:00", "2026-07-06T10:00:00",
                         label="A")


def test_facade_describe(fresh_api):
    asst = LifeAssistant(fresh_api)
    d = asst.describe()
    assert "reminders" in d
    assert "schedule" in d
    assert "activities" in d


def test_facade_services_share_memory(fresh_api):
    asst = LifeAssistant(fresh_api)
    u = asst.activities.start("Writing", at="2026-07-06T09:00:00")
    cur = asst.activities.current()
    assert cur.uri == u