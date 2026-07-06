"""Tests for the four voice-assistant adapters (pure transformations)."""
from __future__ import annotations

from selma.voice.adapters import (AlexaAdapter, CortanaAdapter,
                                  GoogleHomeAdapter, SiriAdapter)
from selma.voice.exceptions import UnknownIntentError
from selma.voice.models import VoiceResponse


# -- AlexaAdapter --

def test_alexa_parse_request_flat_slots():
    req = {
        "request": {
            "intent": {
                "name": "RememberIntent",
                "slots": {
                    "subject": {"value": "http://ex/alice"},
                    "predicate": {"value": "http://ex/knows"},
                },
            },
        },
    }
    parsed = AlexaAdapter().parse_request(req)
    assert parsed.intent == "RememberIntent"
    assert parsed.slots == {
        "subject": "http://ex/alice",
        "predicate": "http://ex/knows",
    }


def test_alexa_parse_request_no_slots():
    req = {"request": {"intent": {"name": "ListRemindersIntent", "slots": {}}}}
    parsed = AlexaAdapter().parse_request(req)
    assert parsed.intent == "ListRemindersIntent"
    assert parsed.slots == {}


def test_alexa_parse_request_missing_intent_raises():
    import pytest
    with pytest.raises(UnknownIntentError):
        AlexaAdapter().parse_request({"request": {"intent": {"slots": {}}}})


def test_alexa_format_response_no_card():
    out = AlexaAdapter().format_response(VoiceResponse("hello"))
    assert out["response"]["outputSpeech"]["type"] == "PlainText"
    assert out["response"]["outputSpeech"]["text"] == "hello"
    assert "card" not in out["response"]


def test_alexa_format_response_with_card():
    out = AlexaAdapter().format_response(
        VoiceResponse("hello", card={"title": "Reminder", "content": "x"}))
    assert out["response"]["card"] == {"title": "Reminder", "content": "x"}


# -- SiriAdapter --

def test_siri_parse_request():
    req = {"intent": "RememberIntent",
           "parameters": {"subject": "http://ex/alice"}}
    parsed = SiriAdapter().parse_request(req)
    assert parsed.intent == "RememberIntent"
    assert parsed.slots == {"subject": "http://ex/alice"}


def test_siri_parse_request_missing_intent_raises():
    import pytest
    with pytest.raises(UnknownIntentError):
        SiriAdapter().parse_request({"parameters": {}})


def test_siri_format_response_no_card():
    out = SiriAdapter().format_response(VoiceResponse("hi"))
    assert out["spokenResponse"] == "hi"
    assert out["content"] is None


def test_siri_format_response_with_card():
    out = SiriAdapter().format_response(
        VoiceResponse("hi", card={"k": "v"}))
    assert out["content"] == {"k": "v"}


# -- CortanaAdapter --

def test_cortana_parse_request_entities_to_slots():
    req = {
        "intent": "RememberIntent",
        "entities": [
            {"type": "subject", "value": "http://ex/alice"},
            {"type": "predicate", "value": "http://ex/knows"},
        ],
    }
    parsed = CortanaAdapter().parse_request(req)
    assert parsed.intent == "RememberIntent"
    assert parsed.slots == {
        "subject": "http://ex/alice",
        "predicate": "http://ex/knows",
    }


def test_cortana_parse_request_missing_intent_raises():
    import pytest
    with pytest.raises(UnknownIntentError):
        CortanaAdapter().parse_request({"entities": []})


def test_cortana_format_response_no_card():
    out = CortanaAdapter().format_response(VoiceResponse("hi"))
    assert out["text"] == "hi"
    assert out["card"] is None


def test_cortana_format_response_with_card():
    out = CortanaAdapter().format_response(
        VoiceResponse("hi", card={"k": "v"}))
    assert out["card"] == {"k": "v"}


# -- GoogleHomeAdapter --

def test_google_parse_request():
    req = {"intent": "RememberIntent",
           "params": {"subject": "http://ex/alice"}}
    parsed = GoogleHomeAdapter().parse_request(req)
    assert parsed.intent == "RememberIntent"
    assert parsed.slots == {"subject": "http://ex/alice"}


def test_google_parse_request_missing_intent_raises():
    import pytest
    with pytest.raises(UnknownIntentError):
        GoogleHomeAdapter().parse_request({"params": {}})


def test_google_format_response_no_card():
    out = GoogleHomeAdapter().format_response(VoiceResponse("hi"))
    assert out["fulfillmentText"] == "hi"
    assert out["payload"] is None


def test_google_format_response_with_card():
    out = GoogleHomeAdapter().format_response(
        VoiceResponse("hi", card={"k": "v"}))
    assert out["payload"] == {"k": "v"}