---
name: validation-plan
description: Plan how to test the riskiest assumptions of an opportunity: interview guides, surveys, or small experiments, each with what result would change the decision
code: VP
added: 2026-10-16
type: prompt
---

# Validation Plan

## What Success Looks Like

For the opportunity or assumptions in the cue, `outputs/discovery/<YYYY-MM-DD>-validate-<slug>.md` lists the riskiest assumptions first, and for each one the cheapest test that could prove it wrong, who would run it, and the result that would change the decision, written down before anyone runs it. Interview guides ask about past behavior, not opinions about future features.

## Your Approach

Set your room status to `drafting`. Read the brief and the ledger entries behind it. Rank the assumptions by how much the decision depends on them and how little evidence they have.

For each of the top assumptions, choose the lightest test that fits:

- **Look first:** data the team already has (analytics, ticket counts, the ledger) can often settle it in an hour.
- **Interviews:** five to eight people from the segments that matter, with a guide that asks about the last time it happened ("Tell me about the last refund you chased"), what they did, and what it cost. No leading questions, no pitching.
- **Survey:** for how common something is, once interviews have shown what to ask.
- **Experiment:** a fake door, a concierge test, or a prototype, when behavior matters more than words.

For each test write: the assumption, the method, who to ask or measure and how to reach them (through the PM or the owner in BOND; you never contact people yourself), the success and failure thresholds, and what the team will do in each case.

Write the plan, log `[discovery] validation <slug>: <n> tests`, and end with the hand-back block. Tests that need people's time go to the PM in `follow_ups`. Results, when they come back, become ledger evidence (`source: interview` or `survey` or `analytics`).
