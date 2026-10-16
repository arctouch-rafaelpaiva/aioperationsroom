---
name: post-approved
description: Keep the room's promises by posting what the operator approved and getting the crew to post theirs
code: PA
added: 2026-10-16
type: prompt
---

# Keep the Promises

## What Success Looks Like

At the end of this step, nothing on your project sits approved but unposted without a reason the room can see. Your own approved items are posted exactly as approved, and each has a `done` with the result link or a `failed` with a note. Your crew's approved items are either posted by their owner this run or named in the stand-up as waiting.

## Your Approach

Follow aor-signal's plan, validate, and execute steps for your own items (`--owner aor-agent-pm`, this project). Post the `final_payload` when the operator edited it, otherwise the `payload`. Re-read each item right before posting, because the operator can still reject it or edit it again until the moment you post.

For a specialist's approved item, run that specialist as a subagent with one job: post its approved items through the same steps. If that specialist isn't available in this run, leave the item and log `waiting on <role> to post <item>`. Never post another agent's item yourself. The approval was given to them, with their name on the raised hand.

Open items older than a day are Maestro's to chase with the operator. You only mention them in the stand-up.
