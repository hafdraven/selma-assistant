# User Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create comprehensive user documentation for the Selma assistant platform — a README plus a docs/ tree covering getting started, architecture, API reference, voice commands, and tutorials.

**Architecture:** Markdown files in the repo. README.md is the GitHub landing page; docs/ contains structured reference and tutorial files. All content written from the actual source code signatures. No external tooling.

**Tech Stack:** Markdown. Python 3.14 (for code examples). pyoxigraph 0.5.9. No new dependencies.

## Global Constraints

- All documentation is written in English. No exceptions.
- Every class name, method signature, parameter name, and return type in the API reference must match the actual source code exactly.
- All code examples must be runnable as-is (or clearly marked as fragments).
- Cross-links between docs use relative paths (e.g. `../api-reference/memory.md`).
- The existing `docs/superpowers/specs/` and `docs/superpowers/plans/` files are not modified.
- Git: use `-c user.email=selma@local -c user.name=selma` on commit (no global identity configured).
- The project is at `D:/src/selma`, public on GitHub as `hafdraven/selma-assistant`.

---

## File Structure

```
README.md                          # NEW — GitHub landing page
docs/
├── getting-started.md             # NEW — install, quickstart, first steps
├── architecture.md                # NEW — platform architecture, data flow
├── api-reference/
│   ├── memory.md                  # NEW — selma.memory API reference
│   ├── life.md                    # NEW — selma.life API reference
│   ├── agents.md                  # NEW — selma.agents API reference
│   └── voice.md                   # NEW — selma.voice API reference
├── voice-commands.md              # NEW — end-user voice cheat sheet
├── tutorials/
│   ├── 01-reminders-and-scheduling.md   # NEW — tutorial
│   ├── 02-custom-voice-intent.md        # NEW — tutorial
│   └── 03-custom-agent.md              # NEW — tutorial
├── superpowers/specs/              # EXISTING — unchanged
└── superpowers/plans/              # EXISTING — unchanged
```

10 new files total. Each task creates one file and commits it. Tasks are independent (no task depends on another's output) so they can be parallelized, but they are listed in a logical reading order.

---

### Task 1: README.md

**Files:**
- Create: `README.md`

**Context:** This is the GitHub landing page for `hafdraven/selma-assistant`. The project has four sub-projects: `selma.memory` (RDF/SPARQL memory core), `selma.life` (reminders/scheduling/activities), `selma.agents` (autonomous task execution), `selma.voice` (voice-assistant gateway). 206 tests pass. Python 3.14, pyoxigraph 0.5.9.

- [ ] **Step 1: Write `README.md`**

Write a ~200-line README with these sections:

1. **Title + tagline**: `# Selma` followed by a one-line description: "A Jarvis/Time-Trax-style life-assistant agent platform with RDF/SPARQL semantic memory, scheduling, autonomous task execution, and voice-assistant integration."

2. **Feature highlights** (bullet list):
   - Semantic RDF/SPARQL memory with a custom ontology and self-describing API
   - Life management: reminders, scheduling, activity tracking
   - Autonomous task execution with project coordination
   - Voice-assistant integration: Alexa, Siri, Cortana, Google Home
   - Pluggable backend: embedded Oxigraph now, remote triplestore and managed RDF later

3. **Quick start** (code block):
```bash
git clone https://github.com/hafdraven/selma-assistant.git
cd selma-assistant
pip install -e ".[dev]"
python -c "from selma.memory import MemoryAPI; print('Selma ready')"
```

4. **5-line quickstart example** (Python code block):
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

5. **Architecture at a glance** (ASCII diagram):
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

6. **Sub-project overview table**:

| Sub-project | Purpose | Key classes | API reference |
|-------------|---------|-------------|---------------|
| `selma.memory` | RDF/SPARQL semantic memory core | `MemoryAPI`, `EmbeddedOxigraph`, `BackendConfig` | [docs/api-reference/memory.md](docs/api-reference/memory.md) |
| `selma.life` | Life assistant: reminders, scheduling, activities | `LifeAssistant`, `ReminderService`, `ScheduleService`, `ActivityService` | [docs/api-reference/life.md](docs/api-reference/life.md) |
| `selma.agents` | Autonomous task execution and project coordination | `AgentsAssistant`, `ProjectService`, `TaskService`, `TaskCoordinator`, `AgentRunner` | [docs/api-reference/agents.md](docs/api-reference/agents.md) |
| `selma.voice` | Voice-assistant integration gateway | `VoiceGateway`, `VoiceRouter`, `AlexaAdapter`, `SiriAdapter`, `CortanaAdapter`, `GoogleHomeAdapter` | [docs/api-reference/voice.md](docs/api-reference/voice.md) |

7. **Documentation links** (organized list):
   - **Getting Started**: [docs/getting-started.md](docs/getting-started.md)
   - **Architecture**: [docs/architecture.md](docs/architecture.md)
   - **API Reference**: [memory](docs/api-reference/memory.md) · [life](docs/api-reference/life.md) · [agents](docs/api-reference/agents.md) · [voice](docs/api-reference/voice.md)
   - **Voice Commands**: [docs/voice-commands.md](docs/voice-commands.md)
   - **Tutorials**: [Reminders & Scheduling](docs/tutorials/01-reminders-and-scheduling.md) · [Custom Voice Intent](docs/tutorials/02-custom-voice-intent.md) · [Custom Agent](docs/tutorials/03-custom-agent.md)
   - **Design Specs**: [Memory Core](docs/superpowers/specs/2026-07-05-selma-memory-core-design.md) · [Life](docs/superpowers/specs/2026-07-06-selma-life-design.md) · [Agents](docs/superpowers/specs/2026-07-06-selma-agents-design.md) · [Voice](docs/superpowers/specs/2026-07-06-selma-voice-design.md)

8. **Development**:
```bash
pip install -e ".[dev]"
pytest -v          # 206 tests
```

9. **License**: `## License` with `MIT (see LICENSE file)` — or `TBD` if no license file exists.

- [ ] **Step 2: Verify the README renders cleanly**

Run: `head -20 README.md`
Expected: the title, tagline, and first sections appear correctly.

- [ ] **Step 3: Commit**

```bash
git add README.md
git -c user.email=selma@local -c user.name=selma commit -m "docs: add README.md GitHub landing page"
```

---

### Task 2: docs/getting-started.md

**Files:**
- Create: `docs/getting-started.md`

**Context:** The getting-started guide is the first thing a developer reads after the README. It must get them from clone to running code in under 10 minutes.

- [ ] **Step 1: Write `docs/getting-started.md`**

Write a ~150-line guide with these sections:

1. **Prerequisites**: Python 3.11+ (developed on 3.14), pip, git.
2. **Installation**: clone, `pip install -e ".[dev]"`, verify import.
3. **Your first memory**: create `EmbeddedOxigraph` + `MemoryAPI`, `remember` a fact, `recall` it. Show the output.
4. **Your first life assistant**: `LifeAssistant`, create a reminder, list it, start/stop an activity.
5. **Your first voice command**: `VoiceGateway` with all subsystems, send an Alexa-format `RememberIntent` request, show the response.
6. **Running the test suite**: `pytest -v`, expected `206 passed`.

Code examples must use the actual API signatures:
```python
from selma.memory import MemoryAPI
from selma.memory.backends.embedded import EmbeddedOxigraph
from pyoxigraph import NamedNode, Literal

memory = MemoryAPI(EmbeddedOxigraph())
memory.remember(
    NamedNode("http://example/meeting"),
    NamedNode("http://example/topic"),
    Literal("budget review"),
    stated_by=NamedNode("https://selma.example/ns/core#self"),
)
rows = memory.recall(subject=NamedNode("http://example/meeting"))
for row in rows:
    print(f"{row['p'].value}: {row['o'].value}")
```

- [ ] **Step 2: Commit**

```bash
git add docs/getting-started.md
git -c user.email=selma@local -c user.name=selma commit -m "docs: add getting-started guide"
```

---

### Task 3: docs/architecture.md

**Files:**
- Create: `docs/architecture.md`

**Context:** The architecture doc explains how the four sub-projects relate and how data flows through the system. It references the design specs for deeper detail.

- [ ] **Step 1: Write `docs/architecture.md`**

Write a ~200-line doc with these sections:

1. **Platform overview**: the four sub-projects and the original vision (Jarvis/Time Trax).
2. **Dependency graph** (same ASCII diagram as README).
3. **The memory core** (`selma.memory`): RDF reification model (blank-node facts with `rdf:subject`/`rdf:predicate`/`rdf:object` + metadata), the custom ontology (9 classes, 18 properties), the `Backend` Protocol with `EmbeddedOxigraph`, the typed API (`remember`/`recall`/`find`/`relate`/`supersede`/`forget`/`ask`/`describe`), light entailment (subclass/inverse/transitive).
4. **The life-assistant core** (`selma.life`): three services, the polling `threading.Timer` scheduler, how facts are stored via `MemoryAPI` (type assertion in named graph + property facts via `remember`).
5. **The agents core** (`selma.agents`): projects, tasks, the task coordinator (claim/complete/block), the `AgentRunner` with executor callables.
6. **The voice gateway** (`selma.voice`): intent router, 4 adapters, `VoiceGateway` facade, 9 built-in intents.
7. **Data flow walkthrough**: "remind me to call mom at 3pm" → Alexa adapter → router → `CreateReminderIntent` → `LifeAssistant.reminders.create()` → `MemoryAPI.remember()` → Oxigraph → response.
8. **Design decisions summary**: condensed table (6-8 rows) from the four specs.

- [ ] **Step 2: Commit**

```bash
git add docs/architecture.md
git -c user.email=selma@local -c user.name=selma commit -m "docs: add architecture overview"
```

---

### Task 4: docs/api-reference/memory.md

**Files:**
- Create: `docs/api-reference/memory.md`
- Read: `src/selma/memory/api.py`, `src/selma/memory/backends/protocol.py`, `src/selma/memory/backends/embedded.py`, `src/selma/memory/config.py`, `src/selma/memory/ontology.py`, `src/selma/memory/exceptions.py`, `src/selma/memory/__init__.py`

**Context:** The API reference for `selma.memory`. Every signature must match the source code exactly. Read the files listed above to get the exact signatures.

- [ ] **Step 1: Write `docs/api-reference/memory.md`**

Write a ~200-line API reference following this template:

1. **Module overview**: 2-3 sentences on what `selma.memory` does.
2. **Public exports table**: from `__all__` in `__init__.py`.
3. **Class: `MemoryAPI`** — constructor `__init__(self, backend)`, then each method with exact signature, return type, exceptions raised, and a 3-5 line code example:
   - `ask(sparql_str, bindings=None)` — passthrough SPARQL
   - `describe()` — returns ontology description
   - `remember(subject, predicate, obj, *, stated_by, confidence=1.0, valid_from=None, valid_to=None, source=None)` — stores a fact
   - `relate(subject, predicate, obj, *, stated_by, valid_from=None, valid_to=None)` — stores a relationship
   - `recall(subject=None, predicate=None, obj=None, *, as_of=None, include_history=False)` — queries facts
   - `find(class_uri, *, filters=None, as_of=None)` — finds entities by class
   - `supersede(fact_uri, new_value, *, stated_by, reason=None)` — retires old fact, asserts new
   - `forget(subject=None, predicate=None, obj=None, *, soft=True, reason=None)` — soft/hard delete
4. **Class: `EmbeddedOxigraph`** — constructor `__init__(self, *, path=None)`.
5. **Class: `BackendConfig`** — dataclass fields `kind`, `path`.
6. **Function: `describe()`** — returns `OntologyDescription`.
7. **Function: `get_backend(config)`** — factory.
8. **Exceptions table**: all 7 exception classes with when they're raised.
9. **Cross-references**: links to `life.md`, `agents.md`, `voice.md`, and the design spec.

- [ ] **Step 2: Commit**

```bash
git add docs/api-reference/memory.md
git -c user.email=selma@local -c user.name=selma commit -m "docs: add selma.memory API reference"
```

---

### Task 5: docs/api-reference/life.md

**Files:**
- Create: `docs/api-reference/life.md`
- Read: `src/selma/life/assistant.py`, `src/selma/life/reminders.py`, `src/selma/life/schedule.py`, `src/selma/life/activity.py`, `src/selma/life/models.py`, `src/selma/life/exceptions.py`, `src/selma/life/__init__.py`

- [ ] **Step 1: Write `docs/api-reference/life.md`**

Write a ~200-line API reference:

1. **Module overview**: `selma.life` is a pure client of `selma.memory`.
2. **Public exports table** from `__all__`.
3. **Class: `LifeAssistant`** — `__init__(self, memory, *, stated_by=None)`, properties `.reminders`, `.schedule`, `.activities`, `.describe()`.
4. **Class: `ReminderService`** — `__init__(self, memory, *, stated_by)`, then each method:
   - `create(fire_at, *, about=None, label=None) -> str`
   - `get(uri) -> Reminder`
   - `list(*, due_before=None, include_fired=False) -> list[Reminder]`
   - `fire(uri, *, now=None) -> None`
   - `check_due(*, now=None) -> list[str]`
   - `start(callback, *, interval=30.0) -> None`
   - `stop() -> None`
5. **Class: `ScheduleService`** — `__init__`, `create`, `list`, `get`, `move`, `cancel`, `conflicts` with exact signatures.
6. **Class: `ActivityService`** — `__init__`, `start`, `stop`, `current`, `history` with exact signatures.
7. **Dataclasses**: `Reminder`, `ScheduleEvent`, `Activity` with their fields.
8. **Exceptions table**: all 7 life exceptions.
9. **Cross-references**: links to `memory.md`, `voice.md`, design spec.

- [ ] **Step 2: Commit**

```bash
git add docs/api-reference/life.md
git -c user.email=selma@local -c user.name=selma commit -m "docs: add selma.life API reference"
```

---

### Task 6: docs/api-reference/agents.md

**Files:**
- Create: `docs/api-reference/agents.md`
- Read: `src/selma/agents/assistant.py`, `src/selma/agents/projects.py`, `src/selma/agents/tasks.py`, `src/selma/agents/coordinator.py`, `src/selma/agents/runner.py`, `src/selma/agents/models.py`, `src/selma/agents/exceptions.py`, `src/selma/agents/__init__.py`

- [ ] **Step 1: Write `docs/api-reference/agents.md`**

Write a ~200-line API reference:

1. **Module overview**: `selma.agents` is a pure client of `selma.memory`.
2. **Public exports table** from `__all__`.
3. **Class: `AgentsAssistant`** — `__init__(self, memory, *, stated_by=None, agent=...)`, properties `.projects`, `.tasks`, `.coordinator`, `.runner`, `.describe()`.
4. **Class: `ProjectService`** — `__init__`, `create`, `get`, `list` with exact signatures.
5. **Class: `TaskService`** — `__init__`, `create`, `set_status`, `set_owner`, `add_dependency`, `get`, `list`, `dependencies` with exact signatures.
6. **Class: `TaskCoordinator`** — `__init__`, `open_tasks`, `blocked_tasks`, `blockers`, `claim`, `complete`, `block` with exact signatures.
7. **Class: `AgentRunner`** — `__init__(self, memory, *, agent=..., stated_by=...)`, `run(task_uri, executor) -> str` with the executor callable signature.
8. **Dataclasses**: `Project`, `Task` with their fields.
9. **Exceptions table**: all agents exceptions.
10. **Cross-references**: links to `memory.md`, `voice.md`, design spec.

- [ ] **Step 2: Commit**

```bash
git add docs/api-reference/agents.md
git -c user.email=selma@local -c user.name=selma commit -m "docs: add selma.agents API reference"
```

---

### Task 7: docs/api-reference/voice.md

**Files:**
- Create: `docs/api-reference/voice.md`
- Read: `src/selma/voice/gateway.py`, `src/selma/voice/router.py`, `src/selma/voice/intents.py`, `src/selma/voice/adapters.py`, `src/selma/voice/models.py`, `src/selma/voice/context.py`, `src/selma/voice/exceptions.py`, `src/selma/voice/__init__.py`

- [ ] **Step 1: Write `docs/api-reference/voice.md`**

Write a ~200-line API reference:

1. **Module overview**: `selma.voice` routes voice-assistant intents to `selma.memory`, `selma.life`, and `selma.agents`.
2. **Public exports table** from `__all__`.
3. **Class: `VoiceGateway`** — `__init__(self, memory, life, agents)`, `handle(assistant_type, request) -> dict`.
4. **Class: `VoiceRouter`** — `__init__(self, context)`, `.context` property, `register(intent, handler)`, `dispatch(intent, slots) -> VoiceResponse`.
5. **Function: `register_builtin_intents(router)`** — registers all 9 built-in intents.
6. **Dataclasses**: `VoiceRequest` (fields: `intent`, `slots`), `VoiceResponse` (fields: `response_text`, `card`), `VoiceContext` (fields: `memory`, `life`, `agents`).
7. **Adapters**: `AlexaAdapter`, `SiriAdapter`, `CortanaAdapter`, `GoogleHomeAdapter` — each with `parse_request(request) -> VoiceRequest` and `format_response(response) -> dict`. Show the expected request/response format for each.
8. **Built-in intents table**: 9 intents with their handler names, required slots, and what they do.
9. **Exceptions table**: all 4 voice exceptions.
10. **Cross-references**: links to `memory.md`, `life.md`, `agents.md`, design spec.

- [ ] **Step 2: Commit**

```bash
git add docs/api-reference/voice.md
git -c user.email=selma@local -c user.name=selma commit -m "docs: add selma.voice API reference"
```

---

### Task 8: docs/voice-commands.md

**Files:**
- Create: `docs/voice-commands.md`
- Read: `src/selma/voice/intents.py`, `src/selma/voice/adapters.py`

- [ ] **Step 1: Write `docs/voice-commands.md`**

Write a ~100-line end-user cheat sheet:

1. **Introduction**: what Selma can do via voice, supported assistants (Alexa, Siri, Cortana, Google Home).
2. **Request format per assistant** (4 tables): show the JSON structure for each adapter's `parse_request` input. Use the actual formats from the adapter code:
   - Alexa: `{"request": {"intent": {"name": "...", "slots": {"key": {"value": "..."}}}}}`
   - Siri: `{"intent": "...", "parameters": {"key": "value"}}`
   - Cortana: `{"intent": "...", "entities": [{"name": "key", "value": "..."}]}`
   - Google Home: `{"intent": "...", "params": {"key": "value"}}`
3. **Built-in intents table**:

| Intent | Example phrase | Required slots | Sample response |
|--------|---------------|----------------|-----------------|
| RememberIntent | "Remember that the meeting topic is budget review" | subject, predicate, object | "Remembered." |
| RecallIntent | "What do you know about the meeting" | subject | "About ...: ..." |
| CreateReminderIntent | "Remind me to call mom at 3pm" | label, time | "Reminder set: ..." |
| ListRemindersIntent | "What are my reminders" | (none) | "Your reminders: ..." |
| CreateTaskIntent | "Create a task write report for project X" | label, project | "Task created: ..." |
| ListTasksIntent | "What are my open tasks for project X" | project | "Your open tasks: ..." |
| StartActivityIntent | "I'm starting deep work" | label | "Started: ..." |
| StopActivityIntent | "I'm done" | (none) | "Stopped activity." |
| DescribeIntent | "What can you do" | (none) | "I can remember, ..." |

4. **Slot format reference**: URIs (full `http://...`), datetimes (`YYYY-MM-DDTHH:MM:SS`), literal text.

- [ ] **Step 2: Commit**

```bash
git add docs/voice-commands.md
git -c user.email=selma@local -c user.name=selma commit -m "docs: add voice commands cheat sheet"
```

---

### Task 9: docs/tutorials/01-reminders-and-scheduling.md

**Files:**
- Create: `docs/tutorials/01-reminders-and-scheduling.md`
- Read: `src/selma/life/assistant.py`, `src/selma/life/reminders.py`, `src/selma/life/schedule.py`, `src/selma/life/activity.py`

- [ ] **Step 1: Write the tutorial**

Write a ~250-line step-by-step tutorial:

1. **Goal**: "In this tutorial you'll build a reminder and scheduling app using `selma.life`. You'll create reminders, fire them with a scheduler, schedule events, detect conflicts, and track activities."
2. **Prerequisites**: install, imports.
3. **Step 1: Set up the assistant** — `EmbeddedOxigraph` + `MemoryAPI` + `LifeAssistant`.
4. **Step 2: Create a reminder** — `life.reminders.create("2026-07-06T09:00:00", label="Team standup")`, list it.
5. **Step 3: Fire due reminders** — `life.reminders.check_due(now="2026-07-06T10:00:00")`, verify the reminder fired.
6. **Step 4: Start the scheduler** — `life.reminders.start(callback, interval=1.0)`, create a past-due reminder, wait, verify callback fired, `stop()`.
7. **Step 5: Schedule an event** — `life.schedule.create("2026-07-06T10:00:00", "2026-07-06T11:00:00", label="Sprint planning")`.
8. **Step 6: Detect a conflict** — try to create an overlapping event, catch `ScheduleConflictError`.
9. **Step 7: Move an event** — `life.schedule.move(uri, "2026-07-06T14:00:00")`.
10. **Step 8: Track an activity** — `life.activities.start("writing", tags=["deep-work"])`, `current()`, `stop(uri)`, `history()`.
11. **Complete script**: a single runnable `.py` file combining all steps.
12. **Next steps**: link to Tutorial 2 and the `life.md` API reference.

- [ ] **Step 2: Commit**

```bash
git add docs/tutorials/01-reminders-and-scheduling.md
git -c user.email=selma@local -c user.name=selma commit -m "docs: add tutorial 1 — reminders and scheduling"
```

---

### Task 10: docs/tutorials/02-custom-voice-intent.md

**Files:**
- Create: `docs/tutorials/02-custom-voice-intent.md`
- Read: `src/selma/voice/gateway.py`, `src/selma/voice/router.py`, `src/selma/voice/intents.py`, `src/selma/voice/models.py`, `src/selma/voice/adapters.py`

- [ ] **Step 1: Write the tutorial**

Write a ~200-line step-by-step tutorial:

1. **Goal**: "Add a custom voice intent to the Selma gateway — a 'RecallFact' intent that recalls everything Selma knows about a subject and returns it as a spoken response."
2. **Prerequisites**: install, imports.
3. **Step 1: Set up the gateway** — `MemoryAPI` + `LifeAssistant` + `AgentsAssistant` + `VoiceGateway`. Register built-in intents.
4. **Step 2: Define a custom intent handler** — a function `def handle_recall_fact(slots, ctx) -> VoiceResponse` that calls `ctx.memory.recall(subject=NamedNode(slots["subject"]))` and builds a response.
5. **Step 3: Register the intent** — `gateway._router.register("RecallFactIntent", handle_recall_fact)`.
6. **Step 4: Test with the Alexa adapter** — build a request dict, call `gateway.handle("alexa", request)`, verify the response.
7. **Step 5: Test with the Google Home adapter** — same intent, different format.
8. **Complete script**: a single runnable `.py` file.
9. **Next steps**: link to Tutorial 3 and the `voice.md` API reference.

Note: the tutorial should use `VoiceRouter` directly (not `gateway._router`) to show the proper API. Construct the router, register the custom intent, then construct the `VoiceGateway` with that router. Read `gateway.py` to see if the router is injectable; if not, show the pattern of creating the router first and passing it to the gateway (or document the access pattern).

- [ ] **Step 2: Commit**

```bash
git add docs/tutorials/02-custom-voice-intent.md
git -c user.email=selma@local -c user.name=selma commit -m "docs: add tutorial 2 — custom voice intent"
```

---

### Task 11: docs/tutorials/03-custom-agent.md

**Files:**
- Create: `docs/tutorials/03-custom-agent.md`
- Read: `src/selma/agents/assistant.py`, `src/selma/agents/projects.py`, `src/selma/agents/tasks.py`, `src/selma/agents/coordinator.py`, `src/selma/agents/runner.py`

- [ ] **Step 1: Write the tutorial**

Write a ~250-line step-by-step tutorial:

1. **Goal**: "Write a custom autonomous agent that creates a project, adds tasks, and executes them using `AgentRunner`."
2. **Prerequisites**: install, imports.
3. **Step 1: Set up the agents assistant** — `MemoryAPI` + `AgentsAssistant`.
4. **Step 2: Create a project** — `agents.projects.create("Documentation sprint", description="Write all user docs")`.
5. **Step 3: Add tasks** — `agents.tasks.create("Write README", project=project_uri)`, `agents.tasks.create("Write API reference", project=project_uri)`, add a dependency.
6. **Step 4: List open tasks** — `agents.coordinator.open_tasks(project_uri)`.
7. **Step 5: Write an executor** — `def my_executor(task_uri: str, memory: MemoryAPI) -> str:` that prints the task and returns a result string.
8. **Step 6: Run the agent** — `agents.runner.run(task_uri, my_executor)`, verify the task status changed to done and the result is stored.
9. **Step 7: Check the result** — query memory for the execution result.
10. **Complete script**: a single runnable `.py` file.
11. **Next steps**: link to the `agents.md` API reference and the design spec.

- [ ] **Step 2: Commit**

```bash
git add docs/tutorials/03-custom-agent.md
git -c user.email=selma@local -c user.name=selma commit -m "docs: add tutorial 3 — custom agent"
```

---

## Self-Review

**1. Spec coverage:**
- §2 file structure: Tasks 1-11 create all 10 new files. ✓
- §3 README content: Task 1. ✓
- §4 getting-started: Task 2. ✓
- §5 architecture: Task 3. ✓
- §6 API reference (4 files): Tasks 4-7. ✓
- §7 voice-commands: Task 8. ✓
- §8 tutorials (3 files): Tasks 9-11. ✓
- §9 English-only: Global Constraints. ✓
- §10 implementation notes (source-accurate, runnable examples, ASCII diagram, relative links, existing specs unchanged): Global Constraints + task instructions. ✓

**2. Placeholder scan:** No "TBD", "TODO", "implement later" in task steps. The license section in Task 1 says "MIT (see LICENSE file) — or TBD if no license file exists" — this is a genuine instruction (check if a LICENSE file exists, act accordingly), not a placeholder. ✓

**3. Type consistency:** All signatures referenced in tasks match the actual source code (verified via grep of class/method definitions). ✓

No issues found. Plan is ready.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-06-user-documentation.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?