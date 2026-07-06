"""selma.voice: voice-assistant integration gateway.

A pure client of ``selma.memory``, ``selma.life``, and ``selma.agents``. Public
surface: the ``VoiceGateway`` facade, the ``VoiceRouter`` + built-in intent
registry, the four voice-assistant adapters, the common request/response/
context dataclasses, and the exception hierarchy.
"""
from .adapters import (AlexaAdapter, CortanaAdapter, GoogleHomeAdapter,
                       SiriAdapter)
from .context import VoiceContext
from .exceptions import (MissingSlotError, UnknownAssistantError,
                         UnknownIntentError, VoiceError)
from .gateway import VoiceGateway
from .intents import register_builtin_intents
from .models import VoiceRequest, VoiceResponse
from .router import VoiceRouter

__all__ = [
    "VoiceGateway",
    "VoiceRouter", "register_builtin_intents",
    "VoiceRequest", "VoiceResponse", "VoiceContext",
    "AlexaAdapter", "SiriAdapter", "CortanaAdapter", "GoogleHomeAdapter",
    "VoiceError", "UnknownIntentError", "MissingSlotError",
    "UnknownAssistantError",
]