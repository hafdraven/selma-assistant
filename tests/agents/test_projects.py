"""Tests for ProjectService (spec §4)."""
from __future__ import annotations

import pytest

from selma.agents.exceptions import ProjectNotFoundError
from selma.agents.models import Project
from selma.memory import terms


def test_create_persists_project(projects, fresh_api):
    u = projects.create("Website", description="Personal site")
    found = fresh_api.find(terms.uri("Project"))
    assert u in [f.value for f in found]


def test_create_stores_label_and_description(projects):
    u = projects.create("Website", description="Personal site")
    p = projects.get(u)
    assert p.label == "Website"
    assert p.description == "Personal site"
    assert p.part_of is None


def test_create_with_part_of(projects):
    parent = projects.create("Platform")
    child = projects.create("Website", part_of=parent)
    p = projects.get(child)
    assert p.part_of == parent


def test_get_unknown_raises(projects):
    with pytest.raises(ProjectNotFoundError):
        projects.get("https://selma.example/ns/agents#project/nope")


def test_list_returns_projects(projects):
    a = projects.create("A")
    b = projects.create("B")
    items = projects.list()
    uris = {p.uri for p in items}
    assert {a, b} == uris


def test_list_returns_project_instances(projects):
    projects.create("A", description="desc")
    items = projects.list()
    assert len(items) == 1
    assert isinstance(items[0], Project)
    assert items[0].label == "A"
    assert items[0].description == "desc"


def test_get_returns_project_instance(projects):
    u = projects.create("A")
    p = projects.get(u)
    assert isinstance(p, Project)
    assert p.uri == u


def test_project_is_frozen(projects):
    u = projects.create("A")
    p = projects.get(u)
    with pytest.raises(Exception):
        p.label = "B"  # frozen dataclass raises FrozenInstanceError