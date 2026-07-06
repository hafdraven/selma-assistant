"""Built-in intent handlers + registration (spec §5).

Each handler is a plain function ``handler(slots, context) -> VoiceResponse``
that extracts the slots it needs (via ``require_slots`` where a slot is
mandatory), calls the relevant Selma subsystem, and builds a ``VoiceResponse``.
``register_builtin_intents`` wires all nine built-ins onto a ``VoiceRouter``.
"""
from __future__ import annotations

from pyoxigraph import NamedNode

from .exceptions import MissingSlotError
from .models import VoiceContext, VoiceResponse
from .router import VoiceRouter

# The default provenance agent for voice-originated facts (same URI the other
# subsystems use for ``default_stated_by()``).
_SELF = "https://selma.example/ns/core#self"


def require_slots(slots: dict[str, str], *names: str) -> None:
    """Raise ``MissingSlotError`` for the first named slot absent from
    ``slots``. Present-but-empty is allowed (handlers may treat empty values
    as they see fit); only a missing key is an error."""
    for name in names:
        if name not in slots:
            raise MissingSlotError(name)


# -- memory intents --

def handle_remember(slots: dict[str, str], ctx: VoiceContext) -> VoiceResponse:
    require_slots(slots, "subject", "predicate", "object")
    subject = slots["subject"]
    predicate = slots["predicate"]
    obj = slots["object"]
    ctx.memory.remember(
        NamedNode(subject), NamedNode(predicate), NamedNode(obj),
        stated_by=NamedNode(_SELF),
    )
    return VoiceResponse("Remembered.", card={"subject": subject})


def handle_recall(slots: dict[str, str], ctx: VoiceContext) -> VoiceResponse:
    require_slots(slots, "subject")
    subject = slots["subject"]
    rows = ctx.memory.recall(subject=NamedNode(subject))
    if not rows:
        return VoiceResponse(f"I don't know anything about {subject} yet.")
    parts = [f"{row['p'].value} {row['o'].value}" for row in rows]
    return VoiceResponse(f"About {subject}: " + "; ".join(parts) + ".")


def handle_describe(slots: dict[str, str], ctx: VoiceContext) -> VoiceResponse:
    desc = ctx.memory.describe()
    classes = [c.label for c in desc.classes]
    return VoiceResponse(
        "I can remember, recall, set reminders, list tasks, and track "
        "activities. I know about: " + ", ".join(classes) + "."
    )


# -- life intents --

def handle_create_reminder(slots: dict[str, str],
                           ctx: VoiceContext) -> VoiceResponse:
    require_slots(slots, "label", "time")
    label = slots["label"]
    time = slots["time"]
    u = ctx.life.reminders.create(time, label=label)
    return VoiceResponse(
        f"Reminder set: {label} at {time}.",
        card={"reminder": u},
    )


def handle_list_reminders(slots: dict[str, str],
                          ctx: VoiceContext) -> VoiceResponse:
    reminders = ctx.life.reminders.list()
    if not reminders:
        return VoiceResponse("You have no reminders.")
    parts = [f"{r.label or r.uri} at {r.fire_at}" for r in reminders]
    return VoiceResponse("Your reminders: " + "; ".join(parts) + ".")


def handle_start_activity(slots: dict[str, str],
                          ctx: VoiceContext) -> VoiceResponse:
    require_slots(slots, "label")
    label = slots["label"]
    u = ctx.life.activities.start(label)
    return VoiceResponse(f"Started activity: {label}.",
                         card={"activity": u})


def handle_stop_activity(slots: dict[str, str],
                         ctx: VoiceContext) -> VoiceResponse:
    current = ctx.life.activities.current()
    if current is None:
        return VoiceResponse("You don't have a running activity.")
    ctx.life.activities.stop(current.uri)
    return VoiceResponse("Activity stopped.")


# -- agents intents --

def handle_create_task(slots: dict[str, str],
                       ctx: VoiceContext) -> VoiceResponse:
    require_slots(slots, "label", "project")
    label = slots["label"]
    project = slots["project"]
    u = ctx.agents.tasks.create(label, project=project)
    return VoiceResponse(f"Task created: {label}.", card={"task": u})


def handle_list_tasks(slots: dict[str, str],
                      ctx: VoiceContext) -> VoiceResponse:
    require_slots(slots, "project")
    project = slots["project"]
    tasks = ctx.agents.coordinator.open_tasks(project)
    if not tasks:
        return VoiceResponse(
            f"You have no open tasks for {project}.")
    parts = [t.label or t.uri for t in tasks]
    return VoiceResponse(
        "Your open tasks: " + "; ".join(parts) + ".")


# -- registration --

_BUILTIN_INTENTS = {
    "RememberIntent": handle_remember,
    "RecallIntent": handle_recall,
    "CreateReminderIntent": handle_create_reminder,
    "ListRemindersIntent": handle_list_reminders,
    "CreateTaskIntent": handle_create_task,
    "ListTasksIntent": handle_list_tasks,
    "StartActivityIntent": handle_start_activity,
    "StopActivityIntent": handle_stop_activity,
    "DescribeIntent": handle_describe,
}


def register_builtin_intents(router: VoiceRouter) -> None:
    """Register all built-in intent handlers on ``router``."""
    for name, handler in _BUILTIN_INTENTS.items():
        router.register(name, handler)