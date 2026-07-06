"""Exception hierarchy for selma.agents (spec §7).

Reuses ``selma.memory.exceptions`` for store-level failures; agents-specific
errors derive from ``MemoryError`` via ``AgentsError``.
"""
from __future__ import annotations

from selma.memory.exceptions import MemoryError


class AgentsError(MemoryError):
    """Base class for all selma.agents errors."""


class ProjectNotFoundError(AgentsError):
    """A project URI was not found in memory."""


class TaskNotFoundError(AgentsError):
    """A task URI was not found in memory."""


class InvalidStatusTransitionError(AgentsError):
    """A status transition was requested that is not allowed."""


class TaskNotClaimableError(AgentsError):
    """``claim``/``run`` called on a task not in an open/in_progress state."""