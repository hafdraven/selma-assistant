"""LifeAssistant — thin facade over the three life services (spec §4)."""
from __future__ import annotations

from .activity import ActivityService
from .reminders import ReminderService
from .schedule import ScheduleService
from .terms import default_stated_by


class LifeAssistant:
    def __init__(self, memory, *, stated_by=None) -> None:
        stated_by = stated_by or default_stated_by()
        self._memory = memory
        self._stated_by = stated_by
        self._reminders = ReminderService(memory, stated_by=stated_by)
        self._schedule = ScheduleService(memory, stated_by=stated_by)
        self._activities = ActivityService(memory, stated_by=stated_by)

    @property
    def reminders(self) -> ReminderService:
        return self._reminders

    @property
    def schedule(self) -> ScheduleService:
        return self._schedule

    @property
    def activities(self) -> ActivityService:
        return self._activities

    def describe(self) -> dict:
        """Return a compact description of the life assistant surface."""
        return {
            "reminders": "create, fire, list, check_due, scheduler",
            "schedule": "create, list, move, cancel, conflicts",
            "activities": "start, stop, current, history",
            "ontology": "selma:Reminder, selma:Event + life: namespace",
        }