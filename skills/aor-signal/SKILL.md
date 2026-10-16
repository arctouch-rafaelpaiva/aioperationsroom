---
name: aor-signal
description: Records AI Operations Room status, asks, approvals, and fires. Use when an aor agent needs to 'update the room', 'raise my hand', 'ask the operator', 'flag a fire', 'record a decision', or get the room 'digest' or 'state'.
---

# aor-signal

This skill is how every AI Operations Room agent (Maestro, project PMs, and specialists) tells the room what is happening. Act as the agent's reporter to the room. The agent decides *what* is true: what it is working on, what it needs from the operator, what it wants to post, what is burning. `scripts/room_signal.py` records it exactly. There are two consumers, and they set the bar:

- **The room** renders characters, raised hands, speech bubbles, and pod health from these events. It needs them current and precise.
- **The operator** decides from them. An ask or approval must stand on its own when read in the room or in a Slack digest, with no conversation attached.

Run `uv run scripts/room_signal.py --help` (and `<command> --help`) for the exact interface. Every command prints JSON. Exit 1 means the request was invalid, and the message names the fix.

## Resolution rules

- Bare paths (e.g. `scripts/room_signal.py`) resolve from this skill's installed directory.
- `{project-root}` → the ops repo checkout (`aor-ops`). Pass it as `--root` when the working directory differs.

## What to record, and when

- **`status`** whenever the agent's activity changes in a way the operator would see: starting a source read, drafting, meeting (stand-up), wrapping, idle. One line of `--task` naming the concrete thing ("Drafting AC for PAY-142"), with `--source-url` when it exists.
- **`ask`** when only the operator can unblock a decision. Ask one question, offer `--options` when the answer space is small, and link context. If a teammate or a source could answer it, don't ask the operator.
- **`approval`** before **any** post to Jira, Notion, GitHub, Figma, or Slack. This is the raised hand. `--payload` (or `--payload-file`) must be the exact final content, because what the operator approves is what gets posted. `--preview` is the one line they see in the digest, and `--rationale` says why it matters.
- **Executing approvals.** A post is irreversible, and the operator can still reject or re-edit until you post it.
  1. **Plan.** At the start of a run, list your ready items (`state items --owner <you> --status approved`, then `--status edited`). Note each item's payload: `final_payload` if it was edited, otherwise `payload`.
  2. **Validate.** Immediately before each post, re-read that one item with `state items --id <item>`. Skip it unless it is still approved or edited and the payload matches what you planned. If it changed, re-plan from the fresh item.
  3. **Execute.** Post exactly that payload. Then run `resolve --decision done --result-url …`, or `--decision failed --note …`.

  An approval left in approved or edited is a promise the room shows as unkept.
- **`risk open` / `risk close`** for blockers and risks as they appear and clear. Blockers carry their open time, and `evaluate` turns overdue ones into fires (default 24h, or a per-project `blocker_fire_hours` in `project.yaml`).
- **`fire`** for the judgment calls the script can't make: `failed_build`, `missed_deadline`, `client_escalation`, `other`. Pass a `--ref` so the same fire deduplicates. `"alert": true` in the output means this is new, so Maestro alerts Slack now. `"alert": false` means it's already known, so stay quiet. Use `--clear` with the same `--ref` when it's resolved. A clear that matches nothing exits 1 and lists the active refs.
- **`evaluate`** at the end of every PM run and every Maestro portfolio watch. Alert on each entry in `new_fires`.
- **`digest`** belongs to Maestro alone. Alert each entry in `fires_to_alert` now, at any hour, and record it with `digest --mark-alerted <keys>`. If `send` is true, post one grouped Slack message to `aor_slack_channel`, threaded under today's brief, with every item and how to answer it. Then record it with `digest --mark-sent <ids> --channel … --thread-ts …`. If `send` is false, post no digest. The script already applied the batch window and quiet hours.
- **`resolve`** with `--by room|slack` records an operator decision that arrives through an agent rather than the room app (for example a Slack reply Maestro reads).

## Gotchas

- **Never edit `aor/room/` by hand or with another tool.** State is folded from append-only per-run event files. A hand edit either corrupts history or silently disappears.
- **Set `AOR_RUN_ID` once per run** (the automation or run id) before the first call. Every call in the run then lands in one file. Without it, everything goes to `local.jsonl` and concurrent cloud runs collide in git.
- **The script never commits.** Commit and push `aor/room/` together with memory changes once, at the end of the run. An unpushed event never reaches the room's source of truth.
- **A live push failure is a warning, not an error** (`"push": "failed"`). Keep going; the room reconciles from git.
- **Fires bypass quiet hours; nothing else does.** Never send an individual Slack message for an ask or approval. Those wait for the digest.

## When the script can't run

Without Python or `uv`, append one JSON line per event to `{project-root}/aor/room/events/<UTC date>/<run id>.jsonl`. Follow the **Storage**, **Event envelope**, and **Event types** sections of `references/room-event-contract.md`. The rest of that file is for the room app, and the live push is never done by hand.

- **Fires.** Before appending a `fire`, search the existing event files for one with the same project, reason, and ref that has no later `fire_clear`. If one exists, don't write a new one; note "already active" instead.
- **Digest.** Skip digest and batching logic.

In both cases, say in the run summary that you used the fallback.
