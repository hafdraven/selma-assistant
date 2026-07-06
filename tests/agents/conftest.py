"""Shared pytest fixtures for selma.agents tests."""
from __future__ import annotations

import pytest
from pyoxigraph import NamedNode

from selma.agents.coordinator import TaskCoordinator
from selma.agents.projects import ProjectService
from selma.agents.runner import AgentRunner
from selma.agents.tasks import TaskService
from selma.agents.terms import AGENT_SELF, default_stated_by, instance


@pytest.fixture
def stated_by() -> NamedNode:
    """The default provenance agent for agents assertions."""
    return default_stated_by()


@pytest.fixture
def projects(fresh_api, stated_by):
    return ProjectService(fresh_api, stated_by=stated_by)


@pytest.fixture
def tasks(fresh_api, stated_by):
    return TaskService(fresh_api, stated_by=stated_by)


@pytest.fixture
def coordinator(fresh_api, stated_by):
    return TaskCoordinator(fresh_api, stated_by=stated_by)


@pytest.fixture
def runner(fresh_api, stated_by):
    return AgentRunner(fresh_api, agent=AGENT_SELF, stated_by=stated_by)


@pytest.fixture
def agent_uri() -> str:
    """A stable agent URI used as a task owner."""
    return AGENT_SELF