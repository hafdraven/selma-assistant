"""VoiceGateway — facade wiring router + adapters + subsystems (spec §6).

The single entry point for a transport layer (HTTP skill handler, Cloud
Function, etc.) that receives a raw assistant request and needs a raw
assistant response.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .adapters import (AlexaAdapter, CortanaAdapter, GoogleHomeAdapter,
                       SiriAdapter)
from .exceptions import UnknownAssistantError
from .intents import register_builtin_intents
from .models import VoiceContext
from .router import VoiceRouter

if TYPE_CHECKING:
    from selma.agents.assistant import AgentsAssistant
    from selma.life.assistant import LifeAssistant
    from selma.memory.api import MemoryAPI


_ADAPTERS = {
    "alexa": AlexaAdapter(),
    "siri": SiriAdapter(),
    "cortana": CortanaAdapter(),
    "google": GoogleHomeAdapter(),
}


class VoiceGateway:
    """Wires the router, adapters, and the three platform subsystems together.

    ``handle(assistant_type, request_dict)`` parses the request via the
    adapter, routes the intent, and returns the response in the assistant's
    format. Unknown ``assistant_type`` raises ``UnknownAssistantError`` (there
    is no adapter to format a response with). Handler-side failures are mapped
    by the router to friendly ``VoiceResponse`` messages and never raise out
    of ``handle``.
    """

    def __init__(self, memory: "MemoryAPI",
                 life: "LifeAssistant",
                 agents: "AgentsAssistant") -> None:
        self._context = VoiceContext(memory=memory, life=life, agents=agents)
        self._router = VoiceRouter(self._context)
        register_builtin_intents(self._router)
        self._adapters = dict(_ADAPTERS)

    def handle(self, assistant_type: str, request: dict) -> dict:
        adapter = self._adapters.get(assistant_type)
        if adapter is None:
            raise UnknownAssistantError(
                f"unknown assistant type: {assistant_type}")
        vr = adapter.parse_request(request)
        resp = self._router.dispatch(vr.intent, vr.slots)
        return adapter.format_response(resp)