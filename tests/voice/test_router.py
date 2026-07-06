"""Tests for VoiceRouter (registry + dispatch + error mapping)."""
from __future__ import annotations

import pytest

from selma.voice.exceptions import MissingSlotError, UnknownIntentError
from selma.voice.models import VoiceResponse
from selma.voice.router import VoiceRouter


def test_dispatch_unknown_intent_returns_friendly_message(router):
    resp = router.dispatch("NopeIntent", {})
    assert resp.response_text == "I don't know how to do that yet"


def test_dispatch_unknown_intent_via_missing_handler(context):
    r = VoiceRouter(context)
    resp = r.dispatch("RememberIntent", {})
    # No handlers registered at all.
    assert resp.response_text == "I don't know how to do that yet"


def test_register_and_dispatch_custom_intent(context):
    r = VoiceRouter(context)

    def handler(slots, ctx):
        return VoiceResponse(f"hi {slots['name']}")

    r.register("GreetIntent", handler)
    resp = r.dispatch("GreetIntent", {"name": "world"})
    assert resp.response_text == "hi world"


def test_handler_exception_returns_generic_error(router):
    def bad_handler(slots, ctx):
        raise ValueError("boom")

    router.register("BadIntent", bad_handler)
    resp = router.dispatch("BadIntent", {})
    assert resp.response_text == "Something went wrong"


def test_missing_slot_error_yields_targeted_message(router):
    def handler(slots, ctx):
        from selma.voice.intents import require_slots
        require_slots(slots, "subject")
        return VoiceResponse("ok")

    router.register("NeedSubject", handler)
    resp = router.dispatch("NeedSubject", {})
    assert resp.response_text == "I need a subject to do that"


def test_missing_slot_error_carries_name():
    err = MissingSlotError("subject")
    assert err.slot_name == "subject"


def test_unknown_intent_error_is_voice_error():
    from selma.voice.exceptions import VoiceError
    assert issubclass(UnknownIntentError, VoiceError)


def test_dispatch_passes_context_to_handler(router, context):
    seen = {}

    def handler(slots, ctx):
        seen["ctx"] = ctx
        return VoiceResponse("ok")

    router.register("CtxIntent", handler)
    router.dispatch("CtxIntent", {})
    assert seen["ctx"] is context


def test_dispatch_passes_slots_to_handler(router):
    seen = {}

    def handler(slots, ctx):
        seen["slots"] = slots
        return VoiceResponse("ok")

    router.register("SlotIntent", handler)
    router.dispatch("SlotIntent", {"a": "1", "b": "2"})
    assert seen["slots"] == {"a": "1", "b": "2"}


def test_require_slots_ok():
    from selma.voice.intents import require_slots
    # Should not raise when all required slots present.
    require_slots({"a": "1", "b": "2"}, "a", "b")


def test_require_slots_missing():
    from selma.voice.intents import require_slots
    with pytest.raises(MissingSlotError) as exc:
        require_slots({"a": "1"}, "a", "b")
    assert exc.value.slot_name == "b"