"""Exception hierarchy for selma.voice (spec §7).

Voice-specific errors derive from ``selma.memory.exceptions.MemoryError`` via
``VoiceError`` so a single base catch covers the whole platform.
"""
from __future__ import annotations

from selma.memory.exceptions import MemoryError


class VoiceError(MemoryError):
    """Base class for all selma.voice errors."""


class UnknownIntentError(VoiceError):
    """``dispatch`` was called with an intent that has no registered handler."""


class MissingSlotError(VoiceError):
    """A handler required a slot that was not provided in the request."""

    def __init__(self, slot_name: str) -> None:
        super().__init__(f"missing required slot: {slot_name}")
        self.slot_name = slot_name


class UnknownAssistantError(VoiceError):
    """``VoiceGateway.handle`` was called with an assistant type that has no
    adapter."""