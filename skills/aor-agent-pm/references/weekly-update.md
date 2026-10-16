---
name: weekly-update
description: Draft the weekly stakeholder update and raise a hand to post it
code: WU
added: 2026-10-16
type: prompt
---

# Weekly Stakeholder Update

## What Success Looks Like

A stakeholder who reads only this update knows what shipped this week, what's next, and what they need to decide or watch, in the voice and format your owner set in BOND. It is drafted in `weekly/<YYYY-Www>.md` and waiting on the operator as a raised hand, never posted unapproved.

## Your Approach

Draw from this week's wraps, `decisions.md`, and the project's risks. Write for the reader your owner named, not for the team: outcomes over activity, dates over adjectives. A slipped date says so, with the new date.

The target is the first Slack channel in `project.yaml` with `use: post`. Raise an aor-signal approval with the exact message as `--payload`, a one-line `--preview`, and the reason in `--rationale`. If the project has no post channel, keep the draft, log it, and say so in Monday's stand-up under **Needs you**.
