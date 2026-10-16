---
name: triage
description: Turn inbox items, source events, and polled changes into routed, owned work
code: TR
added: 2026-10-16
type: prompt
---

# Triage and Route

## What Success Looks Like

Every new inbox item and every source change that matters has an owner and a next move by the end of the run: it was routed to a specialist that ran, or it is visibly waiting for one, or it was dropped with a reason. Nothing is routed twice, and nothing goes to the operator that a role or a source could answer.

## Your Approach

**Collect.** For an event run (GitHub, Slack), the event in your prompt is the input. For a poll run, read each Jira, Figma, and Notion source in `project.yaml` for changes in the last two hours. The window overlaps on purpose, and the inbox key absorbs the repeats. Add each change worth acting on with `inbox add --key <source>|<ref>|<updated>`. An existing key means you already have it.

**Route** with this cue table, then your owner's routing preferences in BOND:

| Signal | Role |
|---|---|
| Feedback, research, stakeholder request, recurring complaint | discovery |
| New or changed epic or story, missing AC, scope question | requirements |
| Notion page edit, a decision made in a thread, docs that disagree | docs |
| Figma change, design question, missing state | design |
| PR opened or updated, technical discussion, dependency change | engineering |
| Bug, failing check, story ready for test, release question | qa |
| Client escalation, deadline at risk, cross-team ask | you, and maybe a fire |

**Hand off.** Run the squad member's skill as a subagent with one scoped cue, as `references/specialist-contract.md` defines it: the project id, the member id when it's a custom member, the inbox item id and link, the task, what done looks like, and the inputs. Mark the item `routed --role <role>`. When the specialist returns, read its `handback` block: mark the item `done` with its summary (or leave it routed with the blocker as the note), triage its `follow_ups` as new inbox items, and put its `questions` in `open-questions.md` with their owners. If the skill isn't available in this run, mark it routed and log `unstaffed: <role>`. Never do the specialist's work yourself.

**Fires and risks.** A failed build on the default branch, a client escalation, or a missed deadline is a fire through aor-signal, with a `--ref` so it deduplicates. A new blocker is `risk open`. Context goes in `risks.md`.

**Questions.** A question only the operator can answer becomes one aor-signal ask with options. A question someone else can answer goes in `open-questions.md` with an owner.

Log one `[pm]` line per routing decision, with the reason when it isn't obvious.
