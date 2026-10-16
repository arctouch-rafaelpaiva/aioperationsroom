---
name: opportunity-brief
description: Write a one-page opportunity brief for a theme: the problem, who has it, the evidence and its strength, the goal, assumptions, and the questions to validate
code: OB
added: 2026-10-16
type: prompt
---

# Opportunity Brief

## What Success Looks Like

The operator and the team can decide whether to pursue the opportunity from one page, `outputs/discovery/<YYYY-MM-DD>-brief-<theme>.md`, and trust it: every claim traces to evidence in the ledger, the strength comes from the script, the goal is named, and what is still a guess is labeled as one. It frames the problem and the range of directions; it doesn't specify a feature.

## Your Approach

Set your room status to `reading`. Run `scripts/evidence.py themes --file outputs/discovery/evidence.yaml` and read the theme's row and its evidence entries. If the theme is an anecdote, say so and stop: a brief needs at least emerging evidence, and the hand-back suggests what evidence to gather.

**Write the brief** with these parts, each short:

- **Problem:** one sentence, from the user's side, without a solution.
- **Who:** the segments and how many people the ledger shows, by channel.
- **Evidence:** the strength, the counts, first and last seen, and three to five quotes with links, including the strongest counter-evidence.
- **Goal:** which goal it moves and how you'd see it in that goal's measure. No goal means say so: the team may still choose it, knowingly.
- **Assumptions:** what must be true for this to be worth solving, each marked as evidenced or a guess.
- **Directions:** two or three different ways the problem could be addressed, at the level of approach, with what each would need to be true.
- **To validate:** the riskiest assumptions and the cheapest way to test each (a validation plan follows if the team says go).

**Share.** Raise one aor-signal `approval --target notion --action update_page --target-url <research page BOND names>` to add the brief, or keep it in outputs if BOND names no page.

**Log and hand back.** Log `[discovery] brief <theme>: <strength>, goal <id>`. Set your status to `idle`, and end with the hand-back block; the decision to pursue it is the operator's, so put it in `follow_ups` for the PM.
