---
name: feedback-synthesis
description: Gather new feedback from the project's sources into the evidence ledger and report the themes, how strong each is, and which goal it serves
code: FS
added: 2026-10-16
type: prompt
---

# Feedback Synthesis

## What Success Looks Like

Every new piece of feedback since the last synthesis is in the evidence ledger, quoted exactly and anonymized, and `outputs/discovery/<YYYY-MM-DD>-themes.md` shows the themes ranked by the script, with their strength, goal, and two or three representative quotes, including one that cuts against the theme when there is one. New themes, themes that got stronger, and themes with no goal are called out. Nothing is posted unless the cue asks.

## Your Approach

Set your room status to `reading`. Find the last synthesis in `outputs/discovery/` (or use the last 30 days). Read each feedback source BOND names, plus the cue's items: Jira tickets with the feedback labels, Notion research pages and interview notes, the Slack channels named, support exports, and stakeholder requests in the inbox. If a source can't be reached, say so in the report; a missing channel biases every theme.

**Add evidence** to `outputs/discovery/evidence.yaml` per `references/evidence-ledger.md`: one entry per person per point, exact quotes, stable anonymous labels. Tag each entry with an existing theme when it fits, create a theme when a new pattern appears (named as a problem, not a feature: "Refunds take too long", not "Refund dashboard"), and leave it untagged when unsure. Link themes to BOND's goals; a theme with no goal stays without one.

**Compute.** Run `uv run scripts/evidence.py check --file outputs/discovery/evidence.yaml` and fix every error. Run `evidence.py themes --file … --since <window start>`, and once more without `--since` to compare against the whole ledger.

**Write it.** The report opens with what changed: new themes, themes that moved up a strength level, and anecdotes worth watching. Then the ranked table (theme, strength, people, channels, mentions, last seen, goal) and, per theme, the representative quotes with their links. Close with the untagged count and the sources you couldn't read.

**Hand back.** Log `[discovery] synthesis: <n> new evidence, <s> strong themes`. Strong themes with a goal and no brief yet go in `follow_ups` (an opportunity brief). Set your status to `idle`, and end with the hand-back block. If the cue asks to share the report, raise one approval for the Notion research page or the project Slack channel BOND names.
