# Project Memory Contract

This is the shared memory of one AI Operations Room project, at `{project-root}/_bmad/memory/aor/projects/<id>/`. The PM curates it. Specialists and Maestro write to it only in the ways listed here. Many cloud runs write at the same moment, so **no two runs may edit the same file**. Each rule below exists to keep that true.

`scripts/project_memory.py` enforces the mechanical parts. Other agents run it from the aor-agent-pm skill (`<skills dir>/aor-agent-pm/scripts/project_memory.py`). Run `--help` for the interface. Set `AOR_RUN_ID` first, because it names this run's files.

| Path | What it holds | Who writes |
|---|---|---|
| `project.yaml` | Registry: sources, roster, fire threshold | `aor-onboard-project` only |
| `automations.md` | The Cursor automation checklist | `aor-onboard-project` only |
| `daily/<local date>/<run id>.md` | Raw log of the day, one line per event: `- HH:MM [role] text (link)` | everyone, through `project_memory.py log` |
| `inbox/<item id>.md` | One item of routed work, with status `new` → `routed` (with role) → `done` or `dropped` | Maestro and triage add items; the PM sets status |
| `standup/<date>.md` | The day's stand-up | PM |
| `eod/<date>.md` | The end-of-day wrap | PM |
| `weekly/<YYYY-Www>.md` | The weekly stakeholder update draft | PM |
| `index.md` | Orientation: what's live, where to look, recent activity | PM |
| `decisions.md` | Dated decisions with the why | PM, from logs and answers |
| `risks.md` | Context for risks and blockers raised through aor-signal | PM |
| `open-questions.md` | Unresolved questions, each with an owner | PM |
| `outputs/<role>/` | Specialist deliverables (briefs, stories, reviews, scenarios) | the owning specialist |
| `squad/<member id>/` | One squad member's memory on this project (persona, bond, memory, session logs), the PM's included (`squad/aor-agent-pm/`), per `references/specialist-contract.md` | that member only |

**Rules.**

- **Logs are append-only and per run.** Never edit another run's log file.
- **One item per inbox file.** Add with `--key` (e.g. `jira|PAY-142|<updated>`), so the same source change never becomes two items.
- **Curated files belong to the PM.** A specialist that finds a decision or a risk logs it. The PM curates it in.
- **Room state is not memory.** Status, asks, approvals, risks, and fires go through aor-signal. `risks.md` only adds context.
- **Commit once, at the end of the run,** with `project_memory.py sync`. It stages the listed projects' memory (squad memory included), `aor/room/`, and Maestro's sanctum when `--sanctum` names it, then rebases and pushes.
