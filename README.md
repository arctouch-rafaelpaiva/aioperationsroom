# AI Operations Room (`aor`)

A BMad module that runs your projects around the clock with one AI squad per project and a conductor across all of them, and asks before anything leaves the room.

- **Maestro** (`aor-agent-maestro`) reads every project: a morning brief, fire alerts, grouped approval digests in Slack, and client email and Slack intake.
- **One squad per project:** a PM (`aor-agent-pm`) runs stand-ups, triage, approved posts, and the end-of-day wrap, and hands work to six specialists: discovery, requirements, design, engineering, QA, and docs. Each member's memory lives with its project, so nothing learned on one project carries to another.
- **The room** (`aor-signal`) records status, asks, approvals, and fires as events. Every external post (Jira, GitHub, Figma, Notion, Slack) waits for your approval.
- **Onboarding** (`aor-onboard-project`) registers a project, its sources and roster, and lists the Cursor automations it needs.

## Install

The room lives in a private **ops repo** that holds its memory and state; scheduled Cursor Cloud Agent runs clone it.

1. Copy the `skills/aor-*` folders into the ops repo's skills directory (for example `.agents/skills/` or `.claude/skills/`).
2. In the ops repo, run the setup skill: "install aor module" (`aor-setup`). It asks for the ritual times, timezone, quiet hours, Slack channel, and fire threshold, writes them to the `aor` section of `_bmad/config.yaml`, registers the module's capabilities, scaffolds `_bmad/memory/aor/` and `aor/room/`, checks your connections, and writes the room's automation checklist.
3. Onboard a project: "onboard project X" (`aor-onboard-project`), then create the automations listed in `_bmad/memory/aor/automations.md` and in the project's `automations.md`.
4. Commit and push the ops repo, then talk to each agent once to hold its First Breath.

**Connections** (Cursor Settings → Tools & MCP): Slack, Atlassian (Jira), Notion, and Gmail. GitHub and Figma work through their MCP servers or a `GH_TOKEN` and `FIGMA_TOKEN` secret. Secrets such as `AOR_SLACK_BOT_TOKEN` go in the Cursor dashboard under Cloud Agents → Secrets, never in the repo.

## Layout

| Path | What it is |
|---|---|
| `skills/aor-setup/` | Module installer: config, help registration, room scaffold, connection checks |
| `skills/aor-signal/` | The room's event log and state (status, asks, approvals, fires) |
| `skills/aor-onboard-project/` | Project registry and automation checklists |
| `skills/aor-agent-maestro/` | Cross-project conductor |
| `skills/aor-agent-pm/` | Per-project stage manager, plus the shared project memory script and squad contract |
| `skills/aor-agent-{discovery,requirements,design,engineering,qa,docs}/` | The six specialists |
| `skills/reports/module-plan-ideation.md` | The module plan and build roadmap |

## Tests

Each skill's scripts have unit tests that run on the standard library plus PyYAML:

```bash
for t in skills/aor-*/scripts/tests/test_*.py; do uv run "$t"; done
```

The room app (Vercel) is the next build step and isn't part of this repo yet.
