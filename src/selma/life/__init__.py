"""selma.life: life-assistant core (reminders, scheduling, activity capture).

A pure client of ``selma.memory``. Public surface: three services plus a
thin ``LifeAssistant`` facade.
"""
from .activity import ActivityService
from .assistant import LifeAssistant
from .exceptions import (ActivityAlreadyRunningError, ActivityNotRunningError,
                         LifeError, ReminderNotFoundError, ReminderNotDueError,
                         ReminderSchedulerError, ScheduleConflictError)
from .models import Activity, Reminder, ScheduleEvent
from .reminders import ReminderService
from .schedule import ScheduleService

__all__ = [
    "LifeAssistant",
    "ReminderService", "ScheduleService", "ActivityService",
    "Reminder", "ScheduleEvent", "Activity",
    "LifeError", "ScheduleConflictError", "ReminderNotDueError",
    "ReminderNotFoundError", "ReminderSchedulerError",
    "ActivityNotRunningError", "ActivityAlreadyRunningError",
]