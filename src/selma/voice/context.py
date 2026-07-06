"""VoiceContext re-export.

``VoiceContext`` lives in ``selma.voice.models`` alongside the request/response
dataclasses. It is also exported from ``selma.voice.context`` so tests and
callers can import it by the short, obvious path.
"""
from __future__ import annotations

from .models import VoiceContext

__all__ = ["VoiceContext"]