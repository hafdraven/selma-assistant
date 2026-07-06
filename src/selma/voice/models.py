"""Common data models for selma.voice (spec §2).

Three dataclasses flow through the gateway:

- ``VoiceRequest``  — assistant-independent request (intent name + slots dict).
- ``VoiceResponse`` — assistant-independent reply (response text + optional
  card dict).
- ``VoiceContext``  — references to the three Selma subsystems passed to every
  handler.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid import cycles at runtime
    from selma.agents.assistant import AgentsAssistant
    from selma.life.assistant import LifeAssistant
    from selma.memory.api import MemoryAPI


@dataclass
class VoiceRequest:
    """An assistant-independent request: an intent name and a flat
    ``dict[str, str]`` of slot name → value."""

    intent: str
    slots: dict[str, str] = field(default_factory=dict)


@dataclass
class VoiceResponse:
    """An assistant-independent reply: spoken text plus an optional visual
    card payload (a plain dict the adapter may render into the assistant's
    card format)."""

    response_text: str
    card: dict | None = None


@dataclass
class VoiceContext:
    """References to the three Selma subsystems, passed to every intent
    handler."""

    memory: "MemoryAPI"
    life: "LifeAssistant"
    agents: "AgentsAssistant"