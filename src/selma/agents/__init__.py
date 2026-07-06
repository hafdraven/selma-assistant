"""selma.agents: autonomous task execution and project coordination.

A pure client of ``selma.memory``. Public surface: four services plus a thin
``AgentsAssistant`` facade.
"""
from .assistant import AgentsAssistant
from .coordinator import TaskCoordinator
from .exceptions import (AgentsError, InvalidStatusTransitionError,
                         ProjectNotFoundError, TaskNotClaimableError,
                         TaskNotFoundError)
from .models import Project, Task
from .projects import ProjectService
from .runner import AgentRunner
from .tasks import TaskService

__all__ = [
    "AgentsAssistant",
    "ProjectService", "TaskService", "TaskCoordinator", "AgentRunner",
    "Project", "Task",
    "AgentsError", "ProjectNotFoundError", "TaskNotFoundError",
    "InvalidStatusTransitionError", "TaskNotClaimableError",
]