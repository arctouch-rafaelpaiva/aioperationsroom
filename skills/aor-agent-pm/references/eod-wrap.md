---
name: eod-wrap
description: Close the project's day so tomorrow's stand-up starts from the truth
code: EW
added: 2026-10-16
type: prompt
---

# End-of-Day Wrap

## What Success Looks Like

`eod/<today>.md` is the honest close of the day, the first thing tomorrow's stand-up reads. The project's curated memory matches what happened today. Someone reading only the wrap knows what landed, what's still open and with whom, what carries over to tomorrow, and which risks could become fires overnight.

## Your Approach

Set your room status to `wrapping`. Read today's logs, outputs, inbox, open questions, and the project's aor-signal state.

Write the wrap in four short sections: **Done** (with links), **Still open** (owner and next move), **Carry-overs** (what tomorrow's stand-up must start with), and **Risks for tomorrow** (anything near its fire threshold, with hours left). Leave a section out when it's empty.

Then curate this project's memory from the day: decisions into `decisions.md` with the why, closed questions out of `open-questions.md`, context for open risks in `risks.md`, and a refreshed "Recent activity" in `index.md` of a few lines. The daily logs stay as they are, because they are the record.

Then let the squad tend its memory: for each member on the roster with session logs in `squad/<member id>/sessions/` newer than its MEMORY.md `last curated:` date, run its skill as a subagent with `--task curate` (see `references/specialist-contract.md`). Skip members whose skill isn't available in this run.

Log `[pm] wrap written`, and set your status to `idle`.
