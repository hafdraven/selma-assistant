# Selma User Documentation — Design Spec

**Date:** 2026-07-06
**Status:** Approved (design sections)
**Topic:** User documentation for the Selma assistant platform
**Spec language:** English

---

## 1. Scope

This spec covers user documentation for the Selma assistant platform — a public
GitHub repo (`hafdraven/selma-assistant`) with four sub-projects (`selma.memory`,
`selma.life`, `selma.agents`, `selma.voice`) and 206 passing tests, but currently
no README or user-facing documentation.

### Audience

Two audiences:
1. **Developers / integrators** — clone the repo, install, understand the architecture,
   and use the Python APIs in their own code.
2. **End-users** — talk to Alexa/Siri/Cortana/Google Home and want to know what they can
   say and what Selma can do.

### Format

Markdown files in the repo. GitHub renders them natively. No external documentation site
tooling (Sphinx/MkDocs). Matches the existing `docs/superpowers/specs/` format.

### Depth

Standard docs plus tutorials:
- Getting started (install, quickstart)
- Architecture overview
- API reference per sub-project
- Voice command cheat sheet
- Step-by-step tutorials (3)
- Links to existing design specs

---

## 2. File Structure

```
README.md                          # GitHub landing page
docs/
├── getting-started.md             # Install, quickstart, first steps
├── architecture.md                # Platform architecture, sub-project relationships, data flow
├── api-reference/
│   ├── memory.md                  # selma.memory API reference
│   ├── life.md                    # selma.life API reference
│   ├── agents.md                  # selma.agents API reference
│   └── voice.md                   # selma.voice API reference
├── voice-commands.md              # End-user cheat sheet: voice phrases per assistant
├── tutorials/
│   ├── 01-reminders-and-scheduling.md   # Build a reminder app with selma.life
│   ├── 02-custom-voice-intent.md        # Add a custom intent to the voice gateway
│   └── 03-custom-agent.md              # Write a custom autonomous agent with AgentRunner
└── superpowers/specs/              # Existing design specs (unchanged)
```

The existing `docs/superpowers/plans/` directory also stays unchanged.

---

## 3. README.md Content

The README is the GitHub landing page (~200 lines). Sections:

1. **Title + tagline**: "Selma — a Jarvis/Time-Trax-style life-assistant agent platform"
   with a one-sentence pitch.
2. **Feature highlights**: 4-5 bullet points — semantic RDF memory, life management
   (reminders/scheduling/activities), autonomous task execution, voice-assistant
   integration (Alexa/Siri/Cortana/Google Home).
3. **Quick start**: 5-line code block — install, create a memory, remember a fact, recall
   it, fire a reminder. Code that actually runs.
4. **Architecture at a glance**: ASCII diagram showing the four sub-projects and their
   dependency arrows.
5. **Sub-project overview table**: name, purpose, key classes, link to API reference doc.
6. **Documentation links**: organized list — Getting Started, Architecture, API Reference
   (4 links), Voice Commands, Tutorials (3 links), Design Specs (4 links).
7. **Development**: `pip install -e ".[dev]"`, `pytest`, contributing note.
8. **License**: placeholder (MIT or TBD).

Tone: technical but accessible. No marketing fluff. All code examples run as-is.

---

## 4. getting-started.md Content

~150 lines. Sections:

1. **Prerequisites**: Python 3.11+ (developed on 3.14), pip, git.
2. **Installation**: `git clone`, `pip install -e ".[dev]"`, verify with
   `python -c "from selma.memory import MemoryAPI"`.
3. **First memory example**: create `EmbeddedOxigraph`, wrap in `MemoryAPI`, `remember` a
   fact with `stated_by`, `recall` it. Show the output.
4. **First life assistant example**: create `LifeAssistant`, add a reminder, list it,
   start/stop an activity. Show the output.
5. **First voice gateway example**: create `VoiceGateway` with all subsystems, send an
   Alexa-format request, show the response dict.
6. **Running the test suite**: `pytest -v`, expected output (206 passed).

---

## 5. architecture.md Content

~200 lines. Sections:

1. **Platform overview**: the four sub-projects and the original vision (Jarvis/Time Trax).
2. **Dependency graph**: ASCII diagram:
   ```
   selma.memory  ←  selma.life
       ↑           ←  selma.agents
       └──────────── selma.voice → (life, agents)
   ```
3. **The memory core**: RDF reification model (blank-node facts with `rdf:subject`/
   `rdf:predicate`/`rdf:object` + metadata), the custom ontology (9 classes, 18 properties),
   the `Backend` Protocol with `EmbeddedOxigraph`, the typed API surface, the `/describe`
   self-description, light entailment (subclass/inverse/transitive).
4. **The life-assistant core**: three services (reminders, scheduling, activities), the
   polling scheduler, how facts are stored via `MemoryAPI`.
5. **The agents core**: projects, tasks, the task coordinator (claim/complete/block),
   the AgentRunner (sequential autonomous execution with executor callables).
6. **The voice gateway**: intent router, adapters (Alexa/Siri/Cortana/Google Home), the
   `VoiceGateway` facade, the 9 built-in intents.
7. **Data flow**: a worked example — user says "remind me to call mom at 3pm" → Alexa
   adapter parses → router dispatches to CreateReminderIntent → `LifeAssistant.reminders`
   `.create()` → `MemoryAPI.remember()` → Oxigraph store → response back through the
   adapter.
8. **Design decisions summary**: condensed table from the four specs.

---

## 6. API Reference Files

Each `docs/api-reference/*.md` follows this template (~150-200 lines each):

### Template

1. **Module overview**: 2-3 sentences on what the sub-project does and its dependencies.
2. **Public exports table**: class/function name → one-line description (from `__all__`).
3. **Class reference**: for each public class:
   - Constructor signature with parameter types.
   - Methods: name, parameters, return type, exceptions raised.
   - 3-5 line code example per method.
4. **Exceptions**: table of exception class → when it's raised.
5. **Cross-references**: links to related sub-project docs and the design spec.

### Content source

Written from the actual source code — the implementer reads each `__init__.py`, the class
files, and the method signatures. Every signature in the docs matches the code exactly.

### Per-file scope

- **memory.md**: `MemoryAPI` (all 8 methods), `Backend` Protocol, `EmbeddedOxigraph`,
  `BackendConfig`, `describe()`, exception hierarchy.
- **life.md**: `LifeAssistant`, `ReminderService`, `ScheduleService`, `ActivityService`,
  `Reminder`/`ScheduleEvent`/`Activity` dataclasses, exception hierarchy.
- **agents.md**: `AgentsAssistant`, `ProjectService`, `TaskService`, `TaskCoordinator`,
  `AgentRunner`, `Project`/`Task` dataclasses, exception hierarchy.
- **voice.md**: `VoiceGateway`, `VoiceRouter`, `VoiceContext`, `VoiceRequest`/
  `VoiceResponse`, four adapters, `register_builtin_intents`, exception hierarchy.

---

## 7. voice-commands.md Content

~100 lines. End-user cheat sheet. Sections:

1. **Introduction**: what Selma can do via voice, supported assistants.
2. **Request formats**: one table per assistant showing the request structure (intent name,
   slots/params, how values are passed).
3. **Built-in intents table**:

| Intent | Example phrase | Required slots | Sample response |
|--------|---------------|----------------|-----------------|
| RememberIntent | "Remember that the meeting topic is budget review" | subject, predicate, object | "Remembered." |
| RecallIntent | "What do you know about the meeting" | subject | "About http://ex/meeting: ..." |
| CreateReminderIntent | "Remind me to call mom at 3pm" | label, time | "Reminder set: call mom at ..." |
| ListRemindersIntent | "What are my reminders" | (none) | "Your reminders: ..." |
| CreateTaskIntent | "Create a task write report for project X" | label, project | "Task created: write report." |
| ListTasksIntent | "What are my open tasks for project X" | project | "Your open tasks: ..." |
| StartActivityIntent | "I'm starting deep work" | label | "Started: deep work." |
| StopActivityIntent | "I'm done" | (none) | "Stopped activity." |
| DescribeIntent | "What can you do" | (none) | "I can remember, recall, ..." |

4. **Slot format reference**: how to format URIs, datetimes, and values per assistant.

---

## 8. Tutorials

Each tutorial (~200-300 lines) follows this structure:

1. **Goal**: what you'll build, what you'll learn.
2. **Prerequisites**: what to install/import.
3. **Step-by-step**: numbered steps with complete code blocks (not fragments), expected
   output, and explanations of why each step works.
4. **Complete script**: a single runnable `.py` file combining all steps.
5. **Next steps**: link to the next tutorial or relevant API reference.

### Tutorial 1: Reminders & Scheduling (`01-reminders-and-scheduling.md`)

Create a `LifeAssistant`, add a reminder, start the scheduler with a callback, schedule an
event, detect a conflict, move the event, start/stop an activity, query history. Covers
`ReminderService`, `ScheduleService`, `ActivityService`, and the `threading.Timer`
scheduler.

### Tutorial 2: Custom Voice Intent (`02-custom-voice-intent.md`)

Define a new intent handler function (`def handle_weather(slots, ctx) -> VoiceResponse`),
register it on `VoiceRouter`, wire the `VoiceGateway`, send a test request through the
Alexa adapter, verify the response. Covers `VoiceRouter.register`, `VoiceContext`,
`VoiceResponse`, adapter `parse_request`/`format_response`.

### Tutorial 3: Custom Agent (`03-custom-agent.md`)

Create a project, add tasks with dependencies, write an executor function
(`def my_executor(task_uri, memory) -> str`), run the `AgentRunner` on a task, verify
status transitions (open → in_progress → done) and the execution result stored in memory.
Covers `ProjectService`, `TaskService`, `TaskCoordinator`, `AgentRunner`.

---

## 9. English-Only Constraint

All documentation files are written in English. This includes the README, all `docs/`
files, and all tutorials. Code comments in examples are in English. No exceptions.

---

## 10. Implementation Notes

- The implementer reads the actual source code to write accurate API references — no
  guessing signatures. Every class, method, parameter, and return type in the docs must
  match the code.
- Code examples in all docs must be runnable (or clearly marked as fragments if truncated
  for brevity).
- The ASCII architecture diagram in the README and `architecture.md` should be identical.
- Cross-links between docs use relative paths (e.g. `../api-reference/memory.md`).
- The existing `docs/superpowers/specs/` and `docs/superpowers/plans/` files are not
  modified — they are linked from the new documentation.

---

## 11. Decisions Log

| Decision | Choice | Alternatives |
|----------|--------|-------------|
| Audience | Both developer + end-user | Developer only; end-user only |
| Format | Markdown in repo | Markdown + Sphinx/MkDocs site; single README |
| Depth | Standard docs + 3 tutorials | Standard only; minimal README only |
| Structure | README + docs/ tree | Single README; docs/ without README |
| API reference source | Written from actual source code | Generated with pdoc/sphinx-autodoc |
| Tutorial count | 3 (life, voice, agents) | 1; 5+ |
| Voice commands | Cheat sheet table per assistant | Single table; prose only |
| Language | English only | Bilingual; user's language |