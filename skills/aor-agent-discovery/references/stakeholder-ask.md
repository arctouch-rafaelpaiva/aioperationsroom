---
name: stakeholder-ask
description: Turn a stakeholder or client request into the problem underneath, the evidence for it, the goal it serves, and the questions to send back
code: SA
added: 2026-10-16
type: prompt
---

# Stakeholder Ask

## What Success Looks Like

A request ("we need a refund dashboard") becomes a short intake in `outputs/discovery/<YYYY-MM-DD>-ask-<slug>.md`: the ask in the stakeholder's words, the problem it most likely stands for, who has that problem, the evidence for it from the ledger (or that there is none yet), the goal it serves (or that it serves none), and three to five questions that would settle what's actually needed. The stakeholder feels heard, and the team gets a problem instead of a spec.

## Your Approach

Set your room status to `reading`. Read the ask where it was made and its context (the thread, the meeting notes, earlier asks from the same person in the ledger).

**Find the problem.** Ask why until you reach something a user experiences: what can't they do today, when, and what does it cost them? Write the problem as one sentence without the solution in it. If there are several plausible problems, list them.

**Weigh it.** Add the ask to the evidence ledger as a `stakeholder` entry, tagged to the theme it matches (or a new one). Run `scripts/evidence.py themes` and read that theme's strength: an ask matching a strong theme is backed; an ask that is the only voice is an anecdote, which is fine to say kindly.

**Questions.** Draft the questions that would settle it: who exactly hits this, how often, what they do today instead, what "solved" looks like, and what happens if nothing changes. Questions about the problem, not about features.

**Write and route.** Write the intake. You never contact the stakeholder yourself: the questions go to the PM in the hand-back's `follow_ups` ("send these to <stakeholder>"), or as `questions` for a squad member who owns the relationship. If the ask matches a strong theme with a goal, add an opportunity brief to `follow_ups`.

**Log and hand back.** Log `[discovery] ask <slug>: <theme>, <strength>`. Set your status to `idle`, and end with the hand-back block.
