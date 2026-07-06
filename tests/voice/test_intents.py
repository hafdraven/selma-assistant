"""Tests for built-in intent handlers (routes into memory/life/agents)."""
from __future__ import annotations

from pyoxigraph import NamedNode

from selma.memory import terms
from selma.voice.models import VoiceResponse


# -- RememberIntent --

def test_remember_intent_stores_fact(router, fresh_api):
    resp = router.dispatch("RememberIntent", {
        "subject": "http://ex/alice",
        "predicate": "http://ex/knows",
        "object": "http://ex/bob",
    })
    assert resp.response_text == "Remembered."
    rows = fresh_api.recall(subject=NamedNode("http://ex/alice"),
                            predicate=NamedNode("http://ex/knows"))
    assert any(row["o"].value == "http://ex/bob" for row in rows)
    assert resp.card is not None
    assert resp.card["subject"] == "http://ex/alice"


def test_remember_intent_missing_slot(router):
    resp = router.dispatch("RememberIntent", {
        "subject": "http://ex/alice",
        "predicate": "http://ex/knows",
    })
    assert resp.response_text == "I need a object to do that"


# -- RecallIntent --

def test_recall_intent_returns_known_facts(router, fresh_api):
    fresh_api.remember(NamedNode("http://ex/alice"),
                       NamedNode("http://ex/knows"),
                       NamedNode("http://ex/bob"),
                       stated_by=NamedNode("https://selma.example/ns/core#self"))
    resp = router.dispatch("RecallIntent", {"subject": "http://ex/alice"})
    text = resp.response_text
    assert "http://ex/alice" in text
    assert "http://ex/bob" in text


def test_recall_intent_unknown_subject(router):
    resp = router.dispatch("RecallIntent", {"subject": "http://ex/nobody"})
    assert "http://ex/nobody" in resp.response_text


def test_recall_intent_missing_slot(router):
    resp = router.dispatch("RecallIntent", {})
    assert resp.response_text == "I need a subject to do that"


# -- CreateReminderIntent --

def test_create_reminder_intent(router, life):
    resp = router.dispatch("CreateReminderIntent", {
        "label": "Stand up",
        "time": "2026-07-10T09:00:00",
    })
    assert resp.response_text == "Reminder set: Stand up at 2026-07-10T09:00:00."
    reminders = life.reminders.list()
    assert len(reminders) == 1
    assert reminders[0].label == "Stand up"
    assert resp.card is not None
    assert resp.card["reminder"] == reminders[0].uri


def test_create_reminder_intent_missing_slot(router):
    resp = router.dispatch("CreateReminderIntent", {"label": "Stand up"})
    assert resp.response_text == "I need a time to do that"


# -- ListRemindersIntent --

def test_list_reminders_empty(router):
    resp = router.dispatch("ListRemindersIntent", {})
    assert resp.response_text == "You have no reminders."


def test_list_reminders_lists_them(router, life):
    life.reminders.create("2026-07-10T09:00:00", label="Stand up")
    life.reminders.create("2026-07-11T08:00:00", label="Coffee")
    resp = router.dispatch("ListRemindersIntent", {})
    text = resp.response_text
    assert "Stand up" in text
    assert "Coffee" in text


# -- CreateTaskIntent --

def test_create_task_intent(router, agents, project_uri):
    resp = router.dispatch("CreateTaskIntent", {
        "label": "Write draft",
        "project": project_uri,
    })
    assert resp.response_text == "Task created: Write draft."
    tasks = agents.tasks.list(project=project_uri)
    assert any(t.label == "Write draft" for t in tasks)
    assert resp.card is not None
    assert resp.card["task"] == tasks[0].uri


def test_create_task_intent_missing_slot(router, project_uri):
    resp = router.dispatch("CreateTaskIntent", {"project": project_uri})
    assert resp.response_text == "I need a label to do that"


# -- ListTasksIntent --

def test_list_tasks_intent_empty(router, project_uri):
    resp = router.dispatch("ListTasksIntent", {"project": project_uri})
    assert project_uri in resp.response_text


def test_list_tasks_intent_lists_open(router, project_uri):
    from selma.agents.terms import AGENT_SELF
    p = project_uri
    u = router.context.agents.tasks.create("Write draft", project=p)
    router.context.agents.coordinator.claim(u, owner=AGENT_SELF)
    resp = router.dispatch("ListTasksIntent", {"project": p})
    assert "Write draft" in resp.response_text


def test_list_tasks_intent_missing_slot(router):
    resp = router.dispatch("ListTasksIntent", {})
    assert resp.response_text == "I need a project to do that"


# -- StartActivityIntent --

def test_start_activity_intent(router, life):
    resp = router.dispatch("StartActivityIntent", {"label": "reading"})
    assert resp.response_text == "Started activity: reading."
    cur = life.activities.current()
    assert cur is not None
    assert cur.label == "reading"
    assert resp.card is not None
    assert resp.card["activity"] == cur.uri


def test_start_activity_intent_missing_slot(router):
    resp = router.dispatch("StartActivityIntent", {})
    assert resp.response_text == "I need a label to do that"


# -- StopActivityIntent --

def test_stop_activity_intent_when_running(router, life):
    life.activities.start("reading")
    resp = router.dispatch("StopActivityIntent", {})
    assert resp.response_text == "Activity stopped."
    assert life.activities.current() is None


def test_stop_activity_intent_when_idle(router):
    resp = router.dispatch("StopActivityIntent", {})
    assert resp.response_text == "You don't have a running activity."


# -- DescribeIntent --

def test_describe_intent(router):
    resp = router.dispatch("DescribeIntent", {})
    text = resp.response_text
    # The describe summary should mention at least one ontology class.
    assert "Entity" in text