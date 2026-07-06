"""Shared pytest fixtures for selma.life tests."""
from __future__ import annotations

import pytest
from pyoxigraph import NamedNode

from selma.life.activity import ActivityService
from selma.life.reminders import ReminderService
from selma.life.schedule import ScheduleService
from selma.life.terms import default_stated_by


@pytest.fixture
def stated_by() -> NamedNode:
    """The default provenance agent for life assertions."""
    return default_stated_by()


@pytest.fixture
def reminders(fresh_api, stated_by):
    return ReminderService(fresh_api, stated_by=stated_by)


@pytest.fixture
def schedule(fresh_api, stated_by):
    return ScheduleService(fresh_api, stated_by=stated_by)


@pytest.fixture
def activities(fresh_api, stated_by):
    return ActivityService(fresh_api, stated_by=stated_by)