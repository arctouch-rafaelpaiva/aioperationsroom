---
title: 'Module Plan'
status: 'complete'
module_name: 'AI Operations Room'
module_code: 'aor'
module_description: 'Animated 8-bit room to monitor and orchestrate project agent teams 24/7'
architecture: 'hybrid: maestro orchestrator + per-project PM + 6 specialists; runtime Cursor Cloud Agents automations; room on Vercel'
standalone: true
expands_module: ''
skills_planned:
  - aor-agent-maestro
  - aor-agent-pm
  - aor-agent-discovery
  - aor-agent-requirements
  - aor-agent-docs
  - aor-agent-design
  - aor-agent-engineering
  - aor-agent-qa
  - aor-onboard-project
  - aor-signal
config_variables:
  - aor_timezone
  - aor_standup_time
  - aor_brief_time
  - aor_eod_time
  - aor_quiet_hours
  - aor_slack_batch_minutes
  - aor_slack_channel
  - aor_blocker_fire_hours
  - aor_require_approval
  - aor_ops_repo
  - aor_room_url
  - aor_room_token
created: '2026-10-15T17:13:50Z'
updated: '2026-10-15T19:49:00Z'
---

# Module Plan

## Vision

The **AI Operations Room** is an animated 8-bit room where a single operator watches and steers AI agent teams working 24/7 across several projects. Each project has a team pod with its own memory and roster (PM plus six specialists). **Maestro**, the manager, sits at a central command desk, runs the daily rhythm with each PM, and acts as the operator's chief of staff.

From a glance at an always-on kiosk screen, the operator should see three things: **everyone's humming along**, **someone needs me**, and **a project is on fire**. Agents read Jira, Figma, GitHub, and Notion. They draft work and raise their hand before posting anything. The operator can respond either in the room or in Slack.

## Architecture

**Status:** decided 2026-10-15.

**Decision:** **Option C (hybrid).**

- **Maestro**: autonomous orchestrator, one per installation.
- **PM**: autonomous team lead and router, one per project.
- **Six specialist agents**: invoked by the PM. They share that project's memory.

**Runtime:** **Cursor Cloud Agents automations** run every scheduled ritual and every event reaction.

**Room hosting:** **Vercel** (Next.js app plus route handlers).

**Rationale:**

- C maps your diagram and responsibility table one-to-one onto the room, so every role is a visible character.
- Only Maestro and the PMs are scheduled and always on.
- The PM is the natural router for Jira, Figma, GitHub, and Notion events.
- Cloud automations give 24/7 execution with no self-hosted scheduler.
- Vercel makes the room reachable by cloud runs and viewable from any screen, including the kiosk and your phone.

### Layers

1. **Agent layer** (BMad skills): Maestro, PM, and six specialists, plus two shared workflows.
2. **Ops repo** (git, source of truth): memory, room state, and approval queue. Cloud automations run against this repo.
3. **Room layer** (Vercel): 8-bit visualization, kiosk mode, onboarding wizard, in-room replies and approvals, Slack interactivity endpoint.

Agents never draw anything. They **write state to the ops repo** and **POST live events to the room**. The room renders from live events and reconciles against git.

### Runtime implications

- **Ephemeral VMs.** Each automation run is a temporary VM on the ops repo. Durable state must be committed and pushed at the end of every run.
- **Triggers.**
  - **Schedules:** PM stand-ups at 08:00 BRT, Maestro brief at 08:30 BRT, optional end-of-day wrap.
  - **Events:** GitHub and Slack triggers where available.
  - **Polling schedules:** Jira, Figma, and Notion when no native trigger exists.
- **Integrations** come through Cursor MCP connections (Jira, Figma, GitHub, Notion, Slack, Gmail). They are configured once, not per run.
- **State sync: both.** Git is the durable, auditable, replayable record. Live events go to `POST {aor_room_url}/api/events` for real-time display.
- **Vercel constraints.**
  - Serverless functions can't hold long-lived WebSockets or a writable disk.
  - Live state therefore goes in **Upstash Redis** (Vercel Marketplace).
  - The browser receives updates via **short polling or SSE with reconnect**.
  - Durable writes from the room (your answers, approvals, onboarding) go to the ops repo through the **GitHub API**.

### Approval rule (locked)

**Any agent** (PM or specialist) may post to Jira, Notion, GitHub, or Slack, but **never without confirmation**.

1. A pending post becomes an **approval request** owned by the agent that drafted it.
2. **That agent's character raises a hand** in the room, and Maestro sends a Slack message.
3. You approve, edit, or reject it from the room or from Slack.
4. The owning agent executes approved posts on its next run (or a PM-triggered run) and records the outcome.

### Notification policy (anti-spam, locked)

You said the worst version of this room is one that **isn't interactive and spams you every minute**.

- **Grouped approvals.** Concurrent approval requests and needs-you items are **batched into one Slack message per window**, set by `aor_slack_batch_minutes` (default 30). Each message is interactive: **Approve all**, approve, edit, or reject per item, plus **Open in room**.
- **One thread per day.** Each day's items go in a single thread under the morning brief, not as new top-level messages.
- **Fires are immediate but deduplicated.** You get one alert per project per fire reason, with updates in the same thread.
- **The room is primary.** The room shows everything live. Slack is the interactive digest and the alert path, not a firehose.
- **Quiet hours.** Outside working hours only fires break through. Everything else waits for the next window or the next brief.

### Memory Architecture

**Pattern:** per-project shared memory, plus Maestro's personal memory, plus the room state bus. All of it lives in the ops repo.

```
{ops-repo}/
  _bmad/memory/
    aor-agent-maestro/            # Maestro personal memory
      index.md
      daily/YYYY-MM-DD.md
      operator.md                 # operator prefs, priorities, comms style
      portfolio.md                # cross-project risks, themes, commitments
      briefs/YYYY-MM-DD.md        # sent morning briefs
    aor/projects/{project-id}/    # shared by PM + specialists of that project
      index.md
      project.yaml                # name, sources (notion/jira/figma/github/slack channels), roster, fire-rule overrides
      eod/YYYY-MM-DD.md           # PM end-of-day wraps
      daily/YYYY-MM-DD.md         # append-only, entries tagged [pm] [discovery] [requirements] [docs] [design] [eng] [qa]
      inbox.md                    # items routed in (from Maestro, events) awaiting PM triage
      decisions.md
      risks.md                    # blockers + risks with opened_at (feeds fire rules)
      open-questions.md
      outputs/{role}/...          # specialist artifacts (briefs, stories, reviews, test scenarios)
  aor/room/                       # machine-readable state bus (also mirrored live to Redis)
    agents.json                   # per agent: project, role, status, current task, updated_at
    projects.json                 # per project: health (green/amber/red), fire reasons
    needs-you.json                # open questions to operator
    approvals.json                # pending/approved/rejected posts with payloads
    events/YYYY-MM-DD.jsonl       # append-only event stream (replay)
```

### Memory Contract

| File | Purpose | Readers | Writers | Shape |
|---|---|---|---|---|
| `projects/{id}/project.yaml` | Project identity, source links, roster, fire overrides | all project agents, Maestro, room | `aor-onboard-project`, room wizard | YAML |
| `projects/{id}/index.md` | Orientation: what's curated, recent activity | all project agents, Maestro | PM (curation) | markdown |
| `projects/{id}/daily/*.md` | Raw chronological log | PM (curation), Maestro (stand-up) | every project agent (append) | timestamped, role-tagged entries |
| `projects/{id}/inbox.md` | Work routed to the PM | PM | Maestro, event reactions | items with source, ts, status |
| `projects/{id}/decisions.md` | Decision log | all | PM, docs steward | dated entries |
| `projects/{id}/risks.md` | Blockers and risks with `opened_at`, severity | PM, Maestro, `aor-signal` | any project agent | YAML-ish list |
| `projects/{id}/open-questions.md` | Unresolved questions | all | any | list with owner |
| `projects/{id}/outputs/{role}/` | Specialist deliverables | PM, Maestro, room (links) | owning specialist | markdown |
| `maestro/operator.md` | Operator preferences and priorities | Maestro | Maestro | curated |
| `maestro/portfolio.md` | Cross-project view | Maestro | Maestro | curated |
| `aor/room/*.json` | Room state | room | `aor-signal` only | JSON (schema in `aor-signal`) |
| `aor/room/events/*.jsonl` | Event stream | room (replay) | `aor-signal` only | one JSON per line |

**Rule:** only `aor-signal` writes `aor/room/`. All other skills call it. This keeps the room contract in one place.

### Cross-Agent Patterns

- **Operator ↔ Maestro:** morning brief, to-dos, priorities, and escalations. Delivered to Slack (`C0C9F0ERP35`) and the room.
- **Maestro ↔ PMs:**
  - At 08:00 each PM holds its project stand-up and writes the outcome.
  - At 08:30 Maestro reads every stand-up, then writes the brief.
  - In the room, PMs walk to Maestro's desk during stand-up.
  - Maestro relays client and context items from email and Slack into each project's `inbox.md`.
- **PM → specialists:** the PM triages its inbox and source events, then invokes a specialist with a scoped task. The specialist writes to `outputs/{role}/` and appends to the daily log.
- **Any agent → operator:** questions and approvals go through `aor-signal` into `needs-you.json` and `approvals.json`. The room shows a raised hand or speech bubble, and Maestro (or the PM) pings Slack. An answer from either surface resolves the item.
- **Fire detection:** `aor-signal` evaluates fire rules on every write. The project area turns red and Maestro alerts Slack immediately, without waiting for the next brief.

## Skills

### aor-agent-maestro

**Type:** agent (autonomous: memory plus PULSE)

**Persona:** Calm, decisive chief of staff and ops manager who runs the room. Speaks in short, prioritized bullets. He leads with what needs the operator, then what's on fire, then what's fine. He is warm with PMs and protective of the operator's time.

**Core Outcome:** The operator starts each day knowing exactly what needs them and why. No project is silently on fire.

**The Non-Negotiable:** Never let a fire or a pending approval go unreported. Never post externally without approval.

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|---|---|---|---|
| Morning brief | Prioritized daily brief after stand-ups | all project stand-up notes, `portfolio.md`, needs-you, approvals | Slack brief (`C0C9F0ERP35`), `briefs/YYYY-MM-DD.md`, room event |
| Portfolio watch | Detect critical failures and fires across projects | all project `risks.md`, room state, fire rules | fire escalations (Slack and room), `portfolio.md` updates |
| Comms intake | Relay client and context from email and Slack to the right PM | Gmail, Slack channels/DMs | items appended to `projects/{id}/inbox.md` |
| Daily to-dos & priorities | Operator to-do list for the day | brief inputs, operator prefs | to-do section in brief, room panel |
| Approval relay | Operator sees every pending post without spam | `approvals.json`, `needs-you.json`, digest from `aor-signal` | **one grouped interactive Slack message per batch window** (threaded under today's brief), reminders only for stale items |
| Operator chat | Answer "what's going on with X?" on demand | question, all memories | answer, optional actions queued for approval |

**Memory:** reads `aor-agent-maestro/*` and every `aor/projects/*/index.md`, `risks.md`, and today's daily log. Writes its own memory and `projects/*/inbox.md`. Daily log tag: `[maestro]`.

**Init Responsibility:** create its memory folder, capture operator preferences (brief style, priorities, quiet hours), and verify that the Slack channel and MCP connections are reachable.

**Activation Modes:** headless (scheduled brief, portfolio watch, comms intake) and interactive (operator chat).

**Tool Dependencies:** Slack MCP (post and read), Gmail MCP (read), `aor-signal`.

**Design Notes:**

- Runs after stand-ups (08:30 BRT) by design.
- Fire alerts bypass the schedule and quiet hours, deduplicated per project and reason.
- Everything else follows the notification policy: grouped, threaded, interactive.

---

### aor-agent-pm

**Type:** agent (autonomous; one instance per project, scoped by `project-id`)

**Persona:** Organized, pragmatic project lead. Routes work, chases loose ends, and keeps the team unblocked. Speaks in decisions needed, blockers, and next actions.

**Core Outcome:** The project's work flows. The right specialist gets each item, unresolved questions are tracked, and the stand-up is honest.

**The Non-Negotiable:** Keep the team honest and unblocked. Its own posts, like everyone's, go through approval (hand up) first.

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|---|---|---|---|
| Daily stand-up | Project status, blockers, risks, asks | daily logs, risks, open questions, source deltas | stand-up note, room "walk to Maestro" event |
| Triage & route | Each inbox or source event assigned to a specialist | `inbox.md`, Jira/Figma/GitHub/Notion events | specialist invocations, routing log |
| Track open questions | No question lost | open-questions, outputs | updated `open-questions.md`, needs-you items |
| Approval follow-up | No approval goes stale; the PM's own drafts are posted once approved | `approvals.json` | PM approval requests (hand up), executed PM posts, nudges to specialists with approved-but-unposted items |
| End-of-day wrap | Close the day: what got done, what's still open, carry-overs, risks for tomorrow | today's daily log, outputs, open questions, approvals | EOD note in memory (feeds the next stand-up and the Maestro brief), room "wrap" event |
| Weekly stakeholder update | Weekly summary draft | week's logs, decisions | update draft (queued for approval) |
| Memory curation | Keep project memory lean and current | daily logs | `index.md`, `decisions.md`, `risks.md` |

**Memory:** project shared memory (read and write). Tag: `[pm]`.

**Init Responsibility:** on first run for a project, validate `project.yaml`, create missing memory files, and post an "arrived" event so characters spawn in the room.

**Activation Modes:** headless (stand-up, event reactions, approval execution) and interactive (operator talks to the PM).

**Tool Dependencies:** Jira, Figma, GitHub, Notion, and Slack MCP; `aor-signal`.

**Design Notes:**

- Rituals run at 08:00 stand-up and `aor_eod_time` wrap (default 18:00 BRT).
- The PM reads the project's **own Slack channels** (from `project.yaml`) for team context.
- Posting is not PM-exclusive. Any agent posts after approval.

---

### Specialist agents (invoked by the PM, share project memory)

All six are **memory agents** (no PULSE). They run when the PM invokes them with a scoped task, read project memory, write to `outputs/{role}/`, and append to the daily log.

Specialists **may post externally** to their natural targets: Jira (requirements, QA), Notion (docs, discovery), GitHub (engineering, QA), Figma comments (design), and project Slack channels. They **always raise their own hand first** through `aor-signal`, and they execute only after you approve.

| Skill | Persona | Core outcome | Key capabilities (inputs → outputs) | Tag |
|---|---|---|---|---|
| `aor-agent-discovery` | Curious, evidence-first researcher | Real problems linked to goals | Feedback synthesis (tickets, Notion research, stakeholder asks → themes, opportunity briefs, questions to validate) | `[discovery]` |
| `aor-agent-requirements` | Precise backlog craftsperson | Ready, testable stories | Opportunity → epics/stories; AC and business rules; gap and dependency check; refinement agenda (Jira, briefs → story drafts) | `[requirements]` |
| `aor-agent-docs` | Meticulous librarian | One consistent truth | Decision logging; contradiction detection across docs, tickets, designs, and implementation; PRD, glossary, and release-note updates (Notion, Jira, Figma, GitHub → corrections) | `[docs]` |
| `aor-agent-design` | Empathetic design partner with edge-case rigor | Designs cover requirements and states | Missing-state review, flow consistency, a11y questions, design↔story mapping (Figma, stories → reviews) | `[design]` |
| `aor-agent-engineering` | Pragmatic senior engineer translator | Implementation matches intent | PR and discussion reading; dependency alerts; implementation-vs-requirement gaps; dev clarification drafts (GitHub, stories → alerts and drafts) | `[eng]` |
| `aor-agent-qa` | Skeptical, fair challenger | Release confidence backed by evidence | Story challenge; test scenarios; coverage gaps; defect triage; release-readiness evidence (stories, PRs, CI → QA reports) | `[qa]` |

**Activation Modes:** headless (invoked by the PM) and interactive (operator can talk to any specialist directly).

**Design Notes:** Personas stay distinct so the room characters feel like a real team. Overlap with `bmm` roles is intentional but independent: this module must work without `bmm`.

---

### aor-onboard-project

**Type:** workflow

**Purpose:** Register a new project or agent so it appears in the room and gets automations.

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|---|---|---|---|
| Onboard project | Project ready to run, with the team knowing exactly where to look | name; **project sources the team must refer to**: Notion (workspace, teamspace, or root pages and databases), Jira (site, project keys, boards, JQL scope), Figma (team, project, or file URLs), GitHub (repos), **project Slack channels** (team context and where the project posts); roster (default 7 roles, add or remove, custom agents); fire overrides | `project.yaml` (sources block validated against the MCP connections), memory scaffold, room "new pod" event, automation setup checklist |
| Update sources | Change which Notion, Jira, Figma, GitHub, or Slack sources a project uses | project, source changes | updated `project.yaml`, room event |
| Add agent | New agent joins a project pod | project, role/name, persona notes | roster update, room spawn event |
| Offboard / archive | Project leaves the room cleanly | project | archived memory, room removal event |

**Design Notes:**

- The **room wizard** collects inputs and commits through the GitHub API. This workflow is the agent-side equivalent and validator, so chat onboarding ("Maestro, add project X") also works.
- Cursor automations may need manual creation in the dashboard. The workflow outputs exact trigger and schedule instructions.

---

### aor-signal

**Type:** workflow (utility, plus a script)

**Purpose:** The single writer of room state. It also evaluates fire rules.

**Capabilities:**

| Capability | Outcome | Inputs | Outputs |
|---|---|---|---|
| Emit status | Agent status and current task updated | agent, project, status, task | `agents.json`, `events/*.jsonl`, `POST /api/events` |
| Raise needs-you | Question to operator surfaced | agent, project, question, options | `needs-you.json`, live event, Slack ping (via caller) |
| Request approval | Pending post queued and owned by the requesting agent | agent, target system, payload, rationale | `approvals.json` (owner = agent), hand-up event on **that agent's** character |
| Batch digest | Concurrent approvals and needs-you items grouped into one interactive Slack message per window | open items since last digest, `aor_slack_batch_minutes`, quiet hours | digest payload (sent by Maestro), with **Approve all** and per-item buttons |
| Evaluate fire | Project health recomputed | `risks.md`, CI status, deadlines, escalations, `aor_blocker_fire_hours` | `projects.json` health (green/amber/red), fire event |

**Design Notes:**

- A deterministic script (Python via `uv`, or Node) owns the JSON schemas, so the room contract is versioned in one place.
- If `POST` fails, it falls back to git-only, and the room catches up on reconcile.

## Configuration

| Variable | Prompt | Default | Result Template | User Setting |
| -------- | ------ | ------- | --------------- | ------------ |
| `aor_timezone` | Timezone for rituals? | `America/Sao_Paulo` (BRT) | `{value}` | yes |
| `aor_standup_time` | PM stand-up time? | `08:00` | `{value}` | yes |
| `aor_brief_time` | Maestro morning brief time (after stand-ups)? | `08:30` | `{value}` | yes |
| `aor_eod_time` | PM end-of-day wrap time? | `18:00` | `{value}` | yes |
| `aor_quiet_hours` | Quiet hours (only fires break through)? | `19:00-07:30` | `{value}` | yes |
| `aor_slack_batch_minutes` | Group approvals and needs-you into one Slack message every N minutes? | `30` | `{value}` | yes |
| `aor_slack_channel` | Operator Slack channel for briefs, grouped approvals, and fire alerts? | `C0C9F0ERP35` (arctouch.slack.com) | `{value}` | no |
| `aor_blocker_fire_hours` | Hours before an open blocker counts as a fire (per-project override)? | `24` | `{value}` | no |
| `aor_require_approval` | Require approval before any external post? | `true` (locked) | `{value}` | no |
| `aor_ops_repo` | Git repo holding memory and room state? | separate private `aor-ops` repo (decided) | `{value}` | no |
| `aor_room_url` | Vercel room URL? | _set after first deploy_ | `{value}` | no |
| `aor_room_token` | Shared secret for the room events API? | _generated at setup_ | `{value}` | no |

**Ritual order:** PM stand-ups at 08:00 BRT, then the Maestro brief at 08:30 BRT, then the PM end-of-day wrap at 18:00 BRT. Each wrap feeds the next morning's stand-up.

**Per-project config** lives in `project.yaml`, not in module config:

- `sources`: Notion, Jira, Figma, GitHub, and Slack channels.
- `roster`.
- Fire overrides.

## External Dependencies

| Dependency | Used by | Setup handling |
|---|---|---|
| Cursor Cloud Agents automations | all scheduled and event runs | setup outputs an automation checklist (schedules, triggers, repo, prompts) |
| MCP: Jira, Figma, GitHub, Notion | PM, specialists | verify connections; guide connect in Cursor |
| MCP: Slack | Maestro, PM | verify post and read to `C0C9F0ERP35` |
| MCP: Gmail | Maestro | verify read access |
| Vercel project | room | deploy room; set env (`AOR_ROOM_TOKEN`, GitHub token, Redis, Slack signing secret) |
| Upstash Redis (Vercel Marketplace) | room live state | provision via Vercel |
| GitHub token or app (ops repo write) | room (answers, approvals, onboarding) | fine-grained token scoped to the ops repo |
| Slack app (interactivity) | approve or answer from Slack | Slack app with interactivity URL pointing at `{aor_room_url}/api/slack` |
| `uv` | `aor-signal` script, BMad skills | install check |

## UI and Visualization

**The room (Vercel, Next.js + Canvas 2D):** borrows patterns from Pixel Agents (MIT): tile map, character sprites, pathfinding, character state machines, and speech bubbles.

- **Layout:**
  - Central Maestro command desk.
  - One **pod per project**: seven desks for PM plus specialists, with the project name and a health light.
  - Pods are added automatically on onboarding.
- **Character states:** idle, walking, typing (drafting), reading (sources), meeting (stand-up), **hand raised** (approval pending), **speech bubble** (needs-you), and alarm (fire).
- **At-a-glance signals (kiosk):**
  - **Green/calm:** agents working.
  - **Amber:** needs-you or approvals, with a count badge.
  - **Red:** a project on fire. The pod flashes and shows the reason.
- **Panels:** click a character or pod to see the current task, recent outputs, open questions, approvals (approve/edit/reject), source links, and the event timeline.
- **Kiosk mode:** fullscreen, no chrome, auto-reconnect, read-only token in the URL, large signals, optional day/night dimming, and optional sounds.
- **Onboarding wizard:**
  1. Project name.
  2. **Sources step:** choose the Notion pages and databases, Jira project and boards, Figma files, GitHub repos, and **project Slack channels** the team should refer to. The wizard validates these against the MCP connections.
  3. Roster picker.
  4. Fire overrides.
  The wizard commits to the ops repo.
- **Approvals tray:** grouped pending posts across all agents, with **Approve all**, edit, and reject. Each item shows which character raised its hand.
- **Replay:** scrub the day's `events/*.jsonl`.
- **Auth:** operator login (Vercel deployment protection or a password) for actions. The kiosk token is view-only.

## Setup Extensions

- Scaffold the **ops repo** structure (`_bmad/memory/aor/...`, `aor/room/...`).
- Scaffold and deploy the **room app** to Vercel, provision Redis, and set env vars. Generate `aor_room_token`.
- Generate the **automation checklist** for Cursor:
  - PM stand-up per project at 08:00 BRT.
  - Maestro brief at 08:30 BRT.
  - Maestro portfolio watch (hourly).
  - Comms intake.
  - Event triggers (GitHub, Slack).
  - Polling for Jira, Figma, and Notion.
- Run MCP connection checks.
- Configure the Slack app interactivity URL.

## Integration

**Standalone.** No dependency on `bmm`. It can coexist with `bmm` and `bmb`, and specialists may optionally reference `bmm` outputs if present.

## Creative Use Cases

- Replay a night shift: watch what each team did overnight in fast-forward.
- Per-agent cost or usage meters shown as health bars.
- Cross-project pattern spotting by Maestro (the same blocker type across pods).
- "War room" mode: when a project is on fire, its pod zooms in and Maestro holds an ad-hoc stand-up.
- Phone view of the same room for on-the-go approvals.

## Ideas Captured

<!-- Phase 1–2 brainstorming: raw capture only -->

### The spark (from user, 2026-10-15)

- **AI Operations Room**: a visual, animated **8-bit digital room** for monitoring all agents working 24/7 across multiple projects: their status, what each is working on, and whether anything is needed from the user.
- Active 8-bit animated characters represent **teams of agents**.
- **Each project team has its own memory and team composition.**
- Must support **onboarding new agents and new projects** into the room.
- **Kiosk mode**: always-on display on a separate screen.
- Sources: architecture diagram and agent responsibility table (`assets/957e5720…png`, `assets/7a6e9d05…png`), reference repo `pixel-agents-main.zip`.

### Architecture sketch (from diagram)

- N project teams (Project 1, 2, 3, …), each with the same 7-role roster. Each writes to its own **Memory (project N)**.
- All project memories flow into one **Maestro Agent** (cross-project hub).

### Roster (from responsibility table)

| Agent | Responsibilities | Typical outputs |
|---|---|---|
| **Maestro** | Watches all project memories for critical failures; daily comms with the user (morning brief, to-dos); reads the user's email and Slack and relays client context to team PMs; runs daily stand-ups with each team PM to surface concerns and brainstorm fixes | Daily Slack brief, risk and outcome reports from PM stand-ups, to-do lists, daily priorities |
| 1. PM coordinator | Routes requests, coordinates specialists, tracks unresolved questions, prepares the daily briefing | Decisions needed, blockers, next actions, weekly stakeholder update |
| 2. Discovery & feedback analyst | Reviews feedback, tickets, research, and stakeholder requests; links recurring problems to goals | Evidence-backed opportunity briefs, feedback themes, questions to validate |
| 3. Requirements & backlog analyst | Turns opportunities into requirements, epics, and stories; finds missing rules, dependencies, and scope | Draft stories, AC, business rules, edge cases, refinement agendas |
| 4. Documentation steward | Maintains docs, records decisions, detects contradictions across docs, tickets, designs, and implementation | Updated PRDs, decision logs, glossary, release notes, doc corrections |
| 5. Design collaboration agent | Checks that designs cover requirements and interaction states; collects designer questions | Missing-state reviews, flow inconsistencies, a11y questions, design↔story maps |
| 6. Engineering collaboration agent | Reads tech discussions and changes; explains intent; flags dependencies and scope changes | Dev clarification drafts, dependency alerts, implementation-vs-requirement gaps |
| 7. QA & acceptance agent | Challenges stories and delivered behavior; links AC to tests and defects | Test scenarios, coverage gaps, defect triage, release-readiness evidence |

### Reference: Pixel Agents (pixel-agents-main)

- Pixel-art office where each agent session is an animated character. Characters walk, sit, type while editing, read while searching, and show a speech bubble when waiting for input or permission.
- Ships as a VS Code extension and a standalone `npx pixel-agents` browser server (Fastify + WebSocket, React 19 + Vite + Canvas 2D, pathfinding, character state machines).
- Agent-agnostic `HookProvider` boundary that produces a normalized `AgentEvent`. The Claude Code reference implementation uses hooks, with JSONL transcript scanning as a fallback.
- Layout editor, **Areas** mapped to workspace folders (roughly one area per project), sub-agents and teams as characters, sound notifications. MIT licensed.
- Its own roadmap includes orchestrator characters, team formation, handoffs, and "offices like save files, one per project". This overlaps strongly with our vision.

### Round 2 answers (user, 2026-10-15)

- **At a glance (kiosk):** all three at once: *someone needs me*, *a project is on fire*, *everyone's humming along*.
- **24/7 behavior:** both scheduled rituals and event-driven reactions.
- **Maestro:** a visible character, the manager orchestrating projects with the user and each PM.
- **Work sources:** Jira, Figma, GitHub, Notion. Slack and email are Maestro's comms channels.
- **Pixel Agents:** build our own room, reusing its libs and patterns.

### Ideas sparked in round 2

- One pod per project plus a central Maestro desk. During stand-up, PM characters walk to Maestro.
- Rituals as animations: morning brief, stand-up gathering, end-of-day wrap.
- Event beats:
  - Jira change: the requirements analyst picks it up.
  - Figma change: the design agent reviews it.
  - GitHub PR: engineering and QA react.
  - Notion edit: the docs steward checks for contradictions.
- Click a character or pod to open a side panel with task, outputs, questions, and source links.
- Per-project health indicator derived from memory.

### Round 3 answers (user, 2026-10-15)

- **Identity:** AI Operations Room, `aor`, standalone.
- **Needs-you:** answer in the room and in Slack, backed by one shared record.
- **Fire triggers:** failed build, missed deadline, client escalation, blocker past the threshold.
- **Onboarding:** wizard in the room.
- *(Open: "worst version" not yet answered.)*

### Round 4 answers (user, 2026-10-15)

- Architecture: Option C. Runtime: Cursor Cloud Agents automations.
- State sync: both (git and a live endpoint).
- Schedule: stand-up at 08:00 BRT, then the Maestro brief at 08:30 BRT.
- Slack: `C0C9F0ERP35`. Fire threshold: 24 hours default.
- Autonomy: always confirm before posting. The PM raises a hand in the room and Maestro sends a Slack message.
- Hosting: **Vercel**.

### Round 5 answers (user, 2026-10-15)

- Add a **PM end-of-day wrap**.
- Onboarding must capture **which Notion, Jira, Figma, and Slack channels** the project team refers to (plus GitHub).
- **Specialists may post too**, but each must **raise its hand** for approval first. Posting is not PM-only.
- Ops repo: **separate private `aor-ops`**.
- **Worst version:** not interactive and spamming every minute. Concurrent approval requests should be **grouped**.

### Final confirmation (user, 2026-10-15)

- Defaults confirmed: EOD wrap at 18:00 BRT, quiet hours 19:00–07:30, Slack batch window 30 min. Plan complete.

## Build Roadmap

Draft order with rationale:

1. **`aor-signal`**: defines the room contract and fire rules. Every other skill depends on it. **Built 2026-10-15** at `skills/aor-signal/`. It has the script `scripts/room_signal.py` and contract `references/room-event-contract.md`. Room state uses event-sourced, per-run JSONL files instead of the shared JSON files sketched in Memory Architecture.
2. **`aor-onboard-project`**: creates project memory and `project.yaml`, which agents need to run. **Built 2026-10-16** at `skills/aor-onboard-project/`. The script `scripts/project_registry.py` owns the `project.yaml` schema. The room draws pods from active `project.yaml` files, and characters arrive through `aor-signal` status events, so the room contract is unchanged.
3. **`aor-agent-pm`**: the project's engine; proves the stand-up, routing, and approval flow end to end. **Built 2026-10-16** at `skills/aor-agent-pm/`. It is an autonomous agent with one PM per squad (user, 2026-10-16): its sanctum lives in each project at `squad/aor-agent-pm/`, next to the project memory, and each project's wrap curates it. Concurrent runs never write the same file: daily logs are `daily/<date>/<run-id>.md`, the inbox is one file per item (`inbox/<id>.md`), and curated files belong to the PM alone. The contract is in `references/project-memory.md`, and the helper script is `scripts/project_memory.py`. This supersedes `daily/YYYY-MM-DD.md` and `inbox.md` in the Memory Architecture above.
4. **`aor-agent-maestro`**: built on the PM stand-up outputs; adds the brief, fire watch, and Slack. **Built 2026-10-16** at `skills/aor-agent-maestro/`. It is an autonomous agent with a fixed name and two automations: `brief` (08:30 weekdays, the daily sanctum curator) and `relay` (every 30 minutes: fire alerts, comms intake, digest-thread replies, grouped digest). Its sanctum replaces `maestro/operator.md`, `portfolio.md`, and `briefs/` above. It posts as a Slack bot (`AOR_SLACK_BOT_TOKEN`, `scripts/slack_post.py`) and falls back to the Slack MCP. Until the room's Slack app exists, approvals happen through thread replies parsed by `scripts/slack_replies.py`, not buttons. Supporting changes: aor-signal records alerted fires (`digest --mark-alerted`, `fires_to_alert`), the contract reserves project id `room` for Maestro's desk, and the PM's `project_memory.py sync` takes several `--project` and a `--sanctum`.
5. **Specialists:** `requirements`, then `qa`, then `engineering`, then `design`, then `docs`, then `discovery`. This order follows the highest-value flow first (tickets to stories to tests to PR checks). **Memory is per squad (user, 2026-10-16):** each project has its own squad, and each member's memory lives inside that project at `projects/<id>/squad/<member id>/`, so nothing learned on one project carries to another. All specialists follow `aor-agent-pm/references/specialist-contract.md` (cue, outputs, approvals, hand-back block, PM-triggered daily curate). **`aor-agent-requirements` built 2026-10-16** at `skills/aor-agent-requirements/`. It drafts stories, reviews readiness, prepares refinement agendas, posts approved items, and curates. `scripts/stories.py` checks drafts and builds the one-batch Jira payload. **`aor-agent-qa` built 2026-10-16** at `skills/aor-agent-qa/`. It writes test scenarios that challenge stories, checks PR coverage against AC, triages defects, gives release verdicts, posts approved comments, and curates. `scripts/qa_matrix.py` traces each AC to scenarios and results and computes go, go-with-risks, or no-go. **`aor-agent-engineering` built 2026-10-16** at `skills/aor-agent-engineering/`. It reads PRs and flags gaps against their stories, raises dependency alerts, drafts dev clarifications, writes change digests, posts approved comments, and curates. `scripts/deps_diff.py` diffs dependency manifests between refs. Code is read with git through Cursor's GitHub connection; PR comments and CI details need the GitHub MCP or a signed-in `gh` (`references/code-access.md`). **`aor-agent-design` built 2026-10-16** at `skills/aor-agent-design/`. It reviews designs for missing states and accessibility, checks flow consistency, maps designs to stories, collects designer questions, posts approved Figma comments, and curates. `scripts/figma_states.py` checks state coverage and reaches Figma's REST API with a `FIGMA_TOKEN` when the Figma MCP isn't connected.
6. **Room app (Vercel):** can start in parallel once the `aor-signal` schemas exist. Build in this order: kiosk view, then panels and approvals, then the onboarding wizard, then Slack interactivity, then replay.
7. **Create Module (CM):** scaffold `aor-setup` with the setup extensions above.

**Next steps:**

1. Build each skill using **Build an Agent (BA)** or **Build a Workflow (BW)**, sharing this plan document as context.
2. When all skills are built, return to **Create Module (CM)** to scaffold the module infrastructure.
