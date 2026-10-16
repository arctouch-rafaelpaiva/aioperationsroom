---
name: standup
description: Run the project's daily stand-up and hand Maestro an honest cue sheet
code: SU
added: 2026-10-16
type: prompt
---

# Daily Stand-up

## What Success Looks Like

`standup/<today>.md` lets Maestro write the morning brief without opening anything else, and lets the operator see in ten seconds whether this project needs them. It is honest: every item that missed its cue says so, with how long and why. It is short: one line per item, an owner on every line.

## Your Approach

Set your room status to `meeting` with the task "Stand-up: <project>". The room walks you to Maestro's desk.

Build the stand-up from the working set (yesterday's wrap, logs since then, the open inbox, open questions), from aor-signal `state` for this project (asks, approvals, risks, fires), and from a quick read of the sources in `project.yaml` for changes since the wrap. Anything new from the sources goes into the inbox for triage; the stand-up only reports it.

Write it as your cue sheet, in this order, leaving out empty sections:

- **Needs you:** open asks and approvals, with ids and how long each has been open. Lead with the one that unblocks the most.
- **On fire / at risk:** active fires and blockers, with how long each has been open against the fire threshold.
- **Holding:** work waiting on something, naming what and who.
- **Unstaffed:** items routed to a specialist that isn't running yet, or work no role owns. Add one line naming squad members whose last hand-back said `calibration: pending`, so the operator knows who still needs a First Breath on this project.
- **Go today:** what each role is doing, one line each.
- **Done since the wrap:** only what landed, with links.

Match the shape your owner asked for in BOND, if they asked for one. Log `[pm] stand-up written` with the file path, and set your status back to `idle` when done.
