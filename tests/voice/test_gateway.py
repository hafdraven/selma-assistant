"""End-to-end tests for the VoiceGateway facade."""
from __future__ import annotations

import pytest
from pyoxigraph import NamedNode

from selma.voice.exceptions import UnknownAssistantError


# -- Alexa end-to-end --

def test_gateway_alexa_remember(gateway, fresh_api):
    req = {
        "request": {
            "intent": {
                "name": "RememberIntent",
                "slots": {
                    "subject": {"value": "http://ex/alice"},
                    "predicate": {"value": "http://ex/knows"},
                    "object": {"value": "http://ex/bob"},
                },
            },
        },
    }
    out = gateway.handle("alexa", req)
    assert out["response"]["outputSpeech"]["text"] == "Remembered."
    rows = fresh_api.recall(subject=NamedNode("http://ex/alice"),
                            predicate=NamedNode("http://ex/knows"))
    assert any(row["o"].value == "http://ex/bob" for row in rows)
    assert out["response"]["card"]["subject"] == "http://ex/alice"


def test_gateway_alexa_unknown_intent(gateway):
    req = {"request": {"intent": {"name": "NopeIntent", "slots": {}}}}
    out = gateway.handle("alexa", req)
    assert out["response"]["outputSpeech"]["text"] == \
        "I don't know how to do that yet"


def test_gateway_alexa_missing_slot(gateway):
    req = {"request": {"intent": {
        "name": "RememberIntent",
        "slots": {
            "subject": {"value": "http://ex/alice"},
            "predicate": {"value": "http://ex/knows"},
        },
    }}}
    out = gateway.handle("alexa", req)
    assert out["response"]["outputSpeech"]["text"] == \
        "I need a object to do that"


# -- Siri end-to-end --

def test_gateway_siri_list_reminders(gateway, life):
    life.reminders.create("2026-07-10T09:00:00", label="Stand up")
    out = gateway.handle("siri",
                         {"intent": "ListRemindersIntent", "parameters": {}})
    assert "Stand up" in out["spokenResponse"]


def test_gateway_siri_describe(gateway):
    out = gateway.handle("siri",
                         {"intent": "DescribeIntent", "parameters": {}})
    assert "Entity" in out["spokenResponse"]


# -- Cortana end-to-end --

def test_gateway_cortana_create_reminder(gateway, life):
    req = {
        "intent": "CreateReminderIntent",
        "entities": [
            {"type": "label", "value": "Stand up"},
            {"type": "time", "value": "2026-07-10T09:00:00"},
        ],
    }
    out = gateway.handle("cortana", req)
    assert out["text"] == "Reminder set: Stand up at 2026-07-10T09:00:00."
    assert len(life.reminders.list()) == 1


# -- Google Home end-to-end --

def test_gateway_google_create_task(gateway, agents, project_uri):
    req = {
        "intent": "CreateTaskIntent",
        "params": {"label": "Write draft", "project": project_uri},
    }
    out = gateway.handle("google", req)
    assert out["fulfillmentText"] == "Task created: Write draft."
    tasks = agents.tasks.list(project=project_uri)
    assert any(t.label == "Write draft" for t in tasks)


def test_gateway_google_start_stop_activity(gateway, life):
    start = gateway.handle("google",
                           {"intent": "StartActivityIntent",
                            "params": {"label": "reading"}})
    assert start["fulfillmentText"] == "Started activity: reading."
    assert life.activities.current() is not None
    stop = gateway.handle("google",
                          {"intent": "StopActivityIntent", "params": {}})
    assert stop["fulfillmentText"] == "Activity stopped."
    assert life.activities.current() is None


# -- Error mapping end-to-end --

def test_gateway_handler_exception_returns_generic(gateway, project_uri):
    # StopActivityIntent with no running activity does NOT raise; it returns a
    # friendly message. To exercise the generic-error path, register a handler
    # that always raises via a custom router path is out of scope for the
    # facade. Instead, verify a handler that raises inside dispatch (via the
    # router) is surfaced as "Something went wrong". We do this by directly
    # poking the gateway's router.
    def bad(slots, ctx):
        raise RuntimeError("boom")
    gateway._router.register("BadIntent", bad)
    out = gateway.handle("google", {"intent": "BadIntent", "params": {}})
    assert out["fulfillmentText"] == "Something went wrong"


def test_gateway_unknown_assistant_raises(gateway):
    with pytest.raises(UnknownAssistantError):
        gateway.handle("hal", {"intent": "DescribeIntent", "params": {}})


def test_gateway_supports_all_assistant_types(gateway):
    for atype, req in [
        ("alexa", {"request": {"intent": {"name": "DescribeIntent",
                                            "slots": {}}}}),
        ("siri", {"intent": "DescribeIntent", "parameters": {}}),
        ("cortana", {"intent": "DescribeIntent", "entities": []}),
        ("google", {"intent": "DescribeIntent", "params": {}}),
    ]:
        out = gateway.handle(atype, req)
        assert out  # non-empty response dict for every assistant type