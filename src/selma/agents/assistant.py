"""AgentsAssistant — thin facade over the agents services (spec §4)."""
from __future__ import annotations

from .coordinator import TaskCoordinator
from .projects import ProjectService
from .runner import AgentRunner
from .tasks import TaskService
from .terms import AGENT_SELF, default_stated_by


class AgentsAssistant:
    def __init__(self, memory, *, stated_by=None, agent: str = AGENT_SELF) -> None:
        stated_by = stated_by or default_stated_by()
        self._memory = memory
        self._stated_by = stated_by
        self._agent = agent
        self._projects = ProjectService(memory, stated_by=stated_by)
        self._tasks = TaskService(memory, stated_by=stated_by)
        self._coordinator = TaskCoordinator(memory, stated_by=stated_by)
        self._runner = AgentRunner(memory, agent=agent, stated_by=stated_by)

    @property
    def projects(self) -> ProjectService:
        return self._projects

    @property
    def tasks(self) -> TaskService:
        return self._tasks

    @property
    def coordinator(self) -> TaskCoordinator:
        return self._coordinator

    @property
    def runner(self) -> AgentRunner:
        return self._runner

    def describe(self) -> dict:
        """Return a compact description of the agents assistant surface."""
        return {
            "projects": "create, list, get",
            "tasks": "create, list, get, set_status, set_owner, "
                     "add_dependency, dependencies",
            "coordinator": "open_tasks, claim, complete, block, "
                           "blocked_tasks, blockers",
            "runner": "run (sequential, single task)",
            "ontology": "selma:Task, selma:Project + agents: namespace",
        }