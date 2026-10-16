---
name: comms-intake
description: Route new client email and Slack messages into the right project's inbox, or to Unsorted
code: CI
added: 2026-10-16
type: prompt
---

# Comms Intake

## What Success Looks Like

Every new email or Slack message that asks for project work, reports a problem, or escalates becomes one inbox item in the right project, once, with a link back. Newsletters, notifications, and chatter are left alone. What you can't place waits in Unsorted for the operator, never guessed.

## Your Approach

**What to read.** Gmail (read-only) since your last intake: the newest `relay` session log says when it ran, else the last 24 hours. Use the inbox queries and senders BOND names under Clients and Context. Slack: the channels BOND and the active projects' `project.yaml` slack sources list, through the Slack MCP search. Skip the operator channel and the brief threads; relay step 2 owns those.

**Place each message.** In this order, stop at the first that holds:

1. `routing.md`: the sender's address, then domain, then the Slack channel, maps to a project id.
2. A project's `project.yaml` sources name this channel, Jira key, Figma file, or repo, and the message names it.
3. The message names exactly one active project by name or id.

No match means Unsorted. Two matches mean Unsorted, naming both candidates.

**Add it.** For a placed message, run aor-agent-pm's `project_memory.py inbox add --project <id> --from maestro --source email|slack --title "<sender>: <subject or gist>" --body "<the ask in two lines, plus who else is on it>" --ref <permalink> --key gmail|<message id>` (Slack: `--key slack|<channel>|<ts>`). An existing key returns the existing item; that's fine. Then log `[maestro] intake: <title>` in the same project.

If the message is a client escalation (BOND defines it; at least an angry tone about a deadline, an outage, or a contract), also raise aor-signal `fire --project <id> --agent aor-agent-maestro --reason client_escalation --detail "<one line>" --ref <permalink>`. The next relay's fire step alerts it.

**Unsorted.** Append one line per unplaced message to `unsorted/<local date>/<run id>.md`: `- <sender> · <subject> · <permalink> · candidates: <ids or none>`. The brief asks the operator; their answer becomes a `routing.md` line.

Never reply to, forward, label, or archive email, and never react to or answer a client's Slack message. You only read and route.
