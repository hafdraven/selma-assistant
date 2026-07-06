"""Voice-assistant adapters (spec §4).

Each adapter is a pure transformation class with two methods:

- ``parse_request(request: dict) -> VoiceRequest``
- ``format_response(response: VoiceResponse) -> dict``

No I/O, no network, no state. The four adapters differ only in the shape of
the request/response dicts they translate. The formats are simplified
representations of each assistant's SDK schema — enough to exercise the
adapter pattern without depending on any real SDK.
"""
from __future__ import annotations

from .exceptions import UnknownIntentError
from .models import VoiceRequest, VoiceResponse


def _intent_name(name) -> str:
    """Extract a non-empty intent name or raise ``UnknownIntentError``."""
    if not name:
        raise UnknownIntentError("request has no intent name")
    return name


class AlexaAdapter:
    """Alexa-format adapter.

    Request: ``request.intent.name`` + ``request.intent.slots`` (a dict of
    slot name → ``{"value": ...}``).
    Response: ``response.outputSpeech.text`` + optional ``response.card``.
    """

    def parse_request(self, request: dict) -> VoiceRequest:
        intent_node = (request.get("request", {}) or {}).get("intent", {}) or {}
        name = _intent_name(intent_node.get("name"))
        raw_slots = intent_node.get("slots", {}) or {}
        slots = {k: v.get("value", "") for k, v in raw_slots.items()}
        return VoiceRequest(intent=name, slots=slots)

    def format_response(self, response: VoiceResponse) -> dict:
        out: dict = {
            "response": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": response.response_text,
                },
            },
        }
        if response.card is not None:
            out["response"]["card"] = response.card
        return out


class SiriAdapter:
    """Siri-format adapter.

    Request: ``intent`` + ``parameters`` (dict[str, str]).
    Response: ``spokenResponse`` + optional ``content``.
    """

    def parse_request(self, request: dict) -> VoiceRequest:
        name = _intent_name(request.get("intent"))
        slots = dict(request.get("parameters", {}) or {})
        return VoiceRequest(intent=name, slots=slots)

    def format_response(self, response: VoiceResponse) -> dict:
        return {
            "spokenResponse": response.response_text,
            "content": response.card,
        }


class CortanaAdapter:
    """Cortana-format adapter.

    Request: ``intent`` + ``entities`` (a list of ``{"type": ..., "value":
    ...}`` dicts; flattened into the slots dict keyed by ``type``).
    Response: ``text`` + optional ``card``.
    """

    def parse_request(self, request: dict) -> VoiceRequest:
        name = _intent_name(request.get("intent"))
        slots: dict[str, str] = {}
        for entity in request.get("entities", []) or []:
            etype = entity.get("type")
            if etype is None:
                continue
            slots[etype] = entity.get("value", "")
        return VoiceRequest(intent=name, slots=slots)

    def format_response(self, response: VoiceResponse) -> dict:
        return {"text": response.response_text, "card": response.card}


class GoogleHomeAdapter:
    """Google Home / Dialogflow-format adapter.

    Request: ``intent`` + ``params`` (dict[str, str]).
    Response: ``fulfillmentText`` + optional ``payload``.
    """

    def parse_request(self, request: dict) -> VoiceRequest:
        name = _intent_name(request.get("intent"))
        slots = dict(request.get("params", {}) or {})
        return VoiceRequest(intent=name, slots=slots)

    def format_response(self, response: VoiceResponse) -> dict:
        return {
            "fulfillmentText": response.response_text,
            "payload": response.card,
        }