"""Shared pytest fixtures for selma.voice tests.

Builds the full three-subsystem stack (memory + life + agents) on top of the
shared ``fresh_api`` fixture from ``tests/conftest.py``.
"""
from __future__ import annotations

import pytest
from pyoxigraph import NamedNode

from selma.agents.assistant import AgentsAssistant
from selma.agents.terms import default_stated_by as agents_stated_by
from selma.life.assistant import LifeAssistant
from selma.life.terms import default_stated_by as life_stated_by
from selma.voice.context import VoiceContext
from selma.voice.gateway import VoiceGateway
from selma.voice.router import VoiceRouter


@pytest.fixture
def stated_by() -> NamedNode:
    """The default provenance agent (same URI across all subsystems)."""
    return NamedNode("https://selma.example/ns/core#self")


@pytest.fixture
def life(fresh_api, stated_by):
    return LifeAssistant(fresh_api, stated_by=stated_by)


@pytest.fixture
def agents(fresh_api, stated_by):
    return AgentsAssistant(fresh_api, stated_by=stated_by)


@pytest.fixture
def context(fresh_api, life, agents):
    return VoiceContext(memory=fresh_api, life=life, agents=agents)


@pytest.fixture
def router(context):
    from selma.voice.intents import register_builtin_intents
    r = VoiceRouter(context)
    register_builtin_intents(r)
    return r


@pytest.fixture
def gateway(fresh_api, life, agents):
    return VoiceGateway(fresh_api, life, agents)


@pytest.fixture
def project_uri(agents):
    """A freshly created project to route task intents against."""
    return agents.projects.create("Website")


@pytest.fixture
def alexa_request():
    """Build an Alexa-format request dict."""
    def _build(intent: str, slots: dict[str, str] | None = None) -> dict:
        slot_objs = {
            name: {"value": value} for name, value in (slots or {}).items()
        }
        return {"request": {"intent": {"name": intent, "slots": slot_objs}}}
    return _build


@pytest.fixture
def siri_request():
    def _build(intent: str, slots: dict[str, str] | None = None) -> dict:
        return {"intent": intent, "parameters": dict(slots or {})}
    return _build


@pytest.fixture
def cortana_request():
    def _build(intent: str, slots: dict[str, str] | None = None) -> dict:
        entities = [{"type": k, "value": v}
                    for k, v in (slots or {}).items()]
        return {"intent": intent, "entities": entities}
    return _build


@pytest.fixture
def google_request():
    def _build(intent: str, slots: dict[str, str] | None = None) -> dict:
        return {"intent": intent, "params": dict(slots or {})}
    return _build