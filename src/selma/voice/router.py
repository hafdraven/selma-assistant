"""VoiceRouter — intent registry + dispatch (spec §3).

Handlers are callables ``handler(slots: dict[str, str], context: VoiceContext)
-> VoiceResponse``. ``dispatch`` looks up the handler, runs it, and maps the
three failure cases (unknown intent, missing required slot, any other handler
exception) to fixed friendly ``VoiceResponse`` messages.
"""
from __future__ import annotations

from .exceptions import MissingSlotError, UnknownIntentError
from .models import VoiceContext, VoiceResponse


class VoiceRouter:
    """Registry of intent name → handler callable, plus dispatch with error
    mapping."""

    def __init__(self, context: VoiceContext) -> None:
        self._context = context
        self._handlers: dict[str, callable] = {}

    @property
    def context(self) -> VoiceContext:
        """The ``VoiceContext`` passed to every handler."""
        return self._context

    def register(self, intent: str, handler) -> None:
        """Register ``handler`` for ``intent`` (overwrites any prior handler)."""
        self._handlers[intent] = handler

    def dispatch(self, intent: str, slots: dict[str, str]) -> VoiceResponse:
        """Look up and invoke the handler for ``intent``.

        Error mapping (spec §7):
          - unknown intent → ``VoiceResponse("I don't know how to do that yet")``
          - ``MissingSlotError`` → ``VoiceResponse("I need a [slot] to do that")``
          - any other handler exception → ``VoiceResponse("Something went wrong")``
        """
        handler = self._handlers.get(intent)
        if handler is None:
            return VoiceResponse("I don't know how to do that yet")
        try:
            return handler(slots, self._context)
        except MissingSlotError as err:
            return VoiceResponse(f"I need a {err.slot_name} to do that")
        except UnknownIntentError:
            return VoiceResponse("I don't know how to do that yet")
        except Exception:
            return VoiceResponse("Something went wrong")