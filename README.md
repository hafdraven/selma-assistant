# Selma

A Jarvis/Time-Trax-style life-assistant agent platform with RDF/SPARQL semantic memory, scheduling, autonomous task execution, and voice-assistant integration.

## Features

- Semantic RDF/SPARQL memory with a custom ontology and self-describing API
- Life management: reminders, scheduling, activity tracking
- Autonomous task execution with project coordination
- Voice-assistant integration: Alexa, Siri, Cortana, Google Home
- Pluggable backend: embedded Oxigraph now, remote triplestore and managed RDF later

## Quick start

```bash
git clone https://github.com/hafdraven/selma-assistant.git
cd selma-assistant
pip install -e ".[dev]"
python -c "from selma.memory import MemoryAPI; print('Selma ready')"
```

## Quickstart example

```python
from selma.memory import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph
from selma.life import LifeAssistant
from pyoxigraph import NamedNode

memory = MemoryAPI(EmbeddedOxigraph(path="~/.selma/memory"))
life = LifeAssistant(memory, stated_by=NamedNode("https://selma.example/ns/core#self"))
life.reminders.create("2026-07-06T09:00:00", label="Team standup")
print(life.reminders.list())
```

## Architecture at a glance

```
┌─────────────────────────────────────────────────────────┐
│                    selma.voice                           │
│  (Alexa / Siri / Cortana / Google Home adapters)        │
└────────────┬──────────────────────────┬─────────────────┘
             │                          │
┌────────────▼──────────┐  ┌───────────▼──────────────┐
│     selma.life        │  │     selma.agents          │
│  (reminders,          │  │  (projects, tasks,        │
│   scheduling,         │  │   coordination,           │
│   activities)         │  │   autonomous execution)   │
└────────────┬──────────┘  └───────────┬──────────────┘
             │                          │
             └──────────┬───────────────┘
                        │
             ┌──────────▼──────────┐
             │    selma.memory     │
             │  (RDF/SPARQL core,  │
             │   ontology, typed   │
             │   API, embedded     │
             │   Oxigraph backend) │
             └─────────────────────┘
```

## Sub-projects

| Sub-project | Purpose | Key classes | API reference |
|-------------|---------|-------------|---------------|
| `selma.memory` | RDF/SPARQL semantic memory core | `MemoryAPI`, `EmbeddedOxigraph`, `BackendConfig` | [docs/api-reference/memory.md](docs/api-reference/memory.md) |
| `selma.life` | Life assistant: reminders, scheduling, activities | `LifeAssistant`, `ReminderService`, `ScheduleService`, `ActivityService` | [docs/api-reference/life.md](docs/api-reference/life.md) |
| `selma.agents` | Autonomous task execution and project coordination | `AgentsAssistant`, `ProjectService`, `TaskService`, `TaskCoordinator`, `AgentRunner` | [docs/api-reference/agents.md](docs/api-reference/agents.md) |
| `selma.voice` | Voice-assistant integration gateway | `VoiceGateway`, `VoiceRouter`, `AlexaAdapter`, `SiriAdapter`, `CortanaAdapter`, `GoogleHomeAdapter` | [docs/api-reference/voice.md](docs/api-reference/voice.md) |

## Documentation

- **Getting Started**: [docs/getting-started.md](docs/getting-started.md)
- **Architecture**: [docs/architecture.md](docs/architecture.md)
- **API Reference**: [memory](docs/api-reference/memory.md) · [life](docs/api-reference/life.md) · [agents](docs/api-reference/agents.md) · [voice](docs/api-reference/voice.md)
- **Voice Commands**: [docs/voice-commands.md](docs/voice-commands.md)
- **Tutorials**: [Reminders & Scheduling](docs/tutorials/01-reminders-and-scheduling.md) · [Custom Voice Intent](docs/tutorials/02-custom-voice-intent.md) · [Custom Agent](docs/tutorials/03-custom-agent.md)
- **Design Specs**: [Memory Core](docs/superpowers/specs/2026-07-05-selma-memory-core-design.md) · [Life](docs/superpowers/specs/2026-07-06-selma-life-design.md) · [Agents](docs/superpowers/specs/2026-07-06-selma-agents-design.md) · [Voice](docs/superpowers/specs/2026-07-06-selma-voice-design.md)

## Development

```bash
pip install -e ".[dev]"
pytest -v          # 206 tests
```

## License

TBD