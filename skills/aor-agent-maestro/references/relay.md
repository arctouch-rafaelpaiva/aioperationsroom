---
name: relay
description: Every 30 minutes, alert new fires, take in comms, apply thread replies, and send the grouped digest
code: RL
added: 2026-10-16
type: prompt
---

# Relay

## What Success Looks Like

Each fire reaches the operator once, within half an hour, at any hour. Their replies in Slack become room decisions within half an hour, exactly once. New asks and approvals reach them grouped, at most once per batch window and never in quiet hours. Client email and Slack land in the right project's inbox, or in Unsorted. A relay with nothing to do takes seconds and posts nothing.

## Your Approach

Set your room status to `reading` with the task "Relay". Keep `AOR_RUN_ID` set for every call. Run these steps in order; each one stands alone, so a failure in one is noted in your session log and the next still runs.

**1. Fires first.** Run aor-signal `digest` (no flags) and read `fires_to_alert`. If any, post one message (one line per fire: project, reason, detail, ref link, who is on it) with `scripts/slack_post.py`, in today's brief thread when `briefs/<today>.md` has a `thread_ts`, otherwise top-level. Fires break quiet hours. After Slack confirms, run `digest --mark-alerted <keys>`, with keys exactly as `project|reason|ref` from the output (an empty ref leaves a trailing `|`).

**2. Replies.** For today's and yesterday's brief threads, read the thread through the Slack MCP (`slack_read_thread`). Write `{"parent": {...}, "replies": [...]}` to a temp file and the output of aor-signal `state items` to another. Then run `scripts/slack_replies.py --thread <file> --state <file> --operator <the Slack user id in BOND>`. If BOND has none (calibration pending), look it up once with the Slack MCP's `slack_read_user_profile` for the authorized user and note it in your session log; never parse replies without `--operator`. Run every argv in `resolves` through `room_signal.py` in order. Each one records a decision the operator made, so it needs no further approval. `skipped` lines with a reason the operator should know (unknown id, already rejected) go into the next digest. Read `unparsed` lines as conversation: a routing answer ("acme is payments") goes to `routing.md` only in the brief run, so note it in your session log and Unsorted for now. Anything else they asked, answer in the thread with `slack_post.py --thread-ts`.

**3. Intake.** Load `references/comms-intake.md` and run it.

**4. Digest.** Run aor-signal `digest` again. If `send` is true, write one message grouped by project: for each item its id, one-line summary, owner, and age, and for approvals the target and preview. Add any `skipped` notes from step 2, and reminders for items open more than a day (from `state items --status open`). End with the reply commands and the room link. Post it in today's brief thread (top-level if there is no brief yet), then run `digest --mark-sent <every listed id> --channel <channel> --thread-ts <ts>`. If `send` is false, post nothing; the `reason` (quiet hours, batch window, nothing new) goes in your session log.

**Never** resolve an item yourself without an operator reply, never post outside the operator channel, and never mark anything sent or alerted before Slack confirmed the post. Set your status back to `idle` when done.
