"""Exception hierarchy for selma.life (spec §7).

Reuses ``selma.memory.exceptions`` for store-level failures; life-specific
errors derive from ``MemoryError`` via ``LifeError``.
"""
from __future__ import annotations

from selma.memory.exceptions import MemoryError


class LifeError(MemoryError):
    """Base class for all selma.life errors."""


class ScheduleConflictError(LifeError):
    """A create/move would overlap an existing scheduled event."""


class ReminderNotDueError(LifeError):
    """``fire`` called on a reminder whose fire time has not yet arrived."""


class ReminderNotFoundError(LifeError):
    """A reminder URI was not found in memory."""


class ReminderSchedulerError(LifeError):
    """The scheduler was started while already running."""


class ActivityNotRunningError(LifeError):
    """``stop`` called on an activity that is not running."""


class ActivityAlreadyRunningError(LifeError):
    """``start`` called while another activity is already running."""