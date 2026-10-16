# Analysis Report: /workspace/skills/aor-signal

Generated: 2026-10-15 · Schema: 2

**Grade: Fair**

> Sound, lean utility with a clean prompt/script boundary. Two script state-machine bugs (terminal resolves, global risk ids) and a missing re-check before posting approved content need fixing before agents depend on it.

The skill's strength is its shape: a 1.2k-token SKILL.md that says when to record what, backed by a tested, deterministic event-sourced script that keeps concurrent cloud runs conflict-free. The main opportunity is hardening the irreversible paths: the script's state machine accepts invalid transitions and collides risk ids across projects, and the approval executor posts without re-validating the item right before it acts.

| Severity | Count |
| --- | --- |
| Critical | 0 |
| High | 4 |
| Medium | 3 |
| Low | 0 |

## Themes

### 1. Script state machine is too permissive

- Root cause: room_signal.py validates the happy path but not terminal states or cross-project identity. Agents trust ok:true, so a closed item can be resurrected, one project's blocker can vanish, and a mis-keyed fire clear leaves a pod red while reporting success.
- Fix: Tighten the script: reject resolves from terminal statuses, key risks by project|risk, and exit 1 when a fire clear matches nothing (listing active refs). Add unit tests for each.
- Findings:
  - `determinism-1` Resolve allows transitions out of terminal item statuses — `scripts/room_signal.py:cmd_resolve`
  - `determinism-2` Risks folded by bare risk id, not project-scoped — `scripts/room_signal.py:fold`
  - `determinism-3` Fire --clear without matching --ref silently no-ops while ok:true — `scripts/room_signal.py:cmd_fire`

### 2. Irreversible posts lack a last-moment check

- Root cause: Approval execution goes fetch → post → resolve. An operator reject/edit can land in between, and the hand-written fallback can re-alert a fire the script would dedupe.
- Fix: Add plan-validate-execute to Executing approvals (re-read the item immediately before posting; post final_payload for edited), and make the no-script fallback check for an active same-key fire before appending one.
- Findings:
  - `enhancement-1` Add plan-validate-execute to approval execution — `SKILL.md:Executing approvals`
  - `enhancement-2` Tighten graceful degradation for fire hand-writes — `SKILL.md:When the script can't run`

### 3. Contract file mixes writer and reader audiences

- Root cause: references/room-event-contract.md serves both the no-script agent fallback and the Vercel room app. The agent fallback pays for Folded state and Live push sections it should not act on.
- Fix: Point the SKILL.md fallback at the Storage, Event envelope, and Event types sections only (or split a write-only contract), keeping Live push and Folded state for the room app.
- Findings:
  - `leanness-1` Folded-state section is ceremony on the agent load path — `references/room-event-contract.md:Folded state`
  - `leanness-2` Live-push API docs invite work the fallback forbids — `references/room-event-contract.md:Live push`

## Strengths

- Event-sourced per-run JSONL files make concurrent Cursor Cloud runs conflict-free in git and give the room free replay.
- Clean intelligence placement: agents judge what is true; the script owns dedup, thresholds, batch windows, and quiet hours.
- Invalid requests exit 1 with a message naming the fix and the valid ids, so agents can self-correct.
- Live push degrades gracefully: git stays the source of truth.
- SKILL.md is destination-shaped and well under budget; gotchas stay inline.

## Recommendations

1. Fix the script state machine (terminal resolves, project-scoped risk ids, loud fire-clear miss) with unit tests. (resolves: determinism-1, determinism-2, determinism-3)
2. Rewrite Executing approvals as plan, validate (re-read the item right before posting), then execute. (resolves: enhancement-1)
3. Scope the fallback to the write sections of the contract and add a fire dedup check to the hand-write path. (resolves: leanness-1, leanness-2, enhancement-2)

## Experience

- **Specialist raises hand** — approval with exact payload → room hand up + Maestro digest → operator approves/edits → agent re-reads item → posts → resolve done
- **Blocker becomes fire** — risk open → PM run evaluate after 24h → new_fires → Maestro alerts Slack once → risk close → evaluate clears
- Headless: Headless-only by design: every command is non-interactive JSON with exit codes, called by other aor agents inside Cursor Cloud automation runs.

## Findings

### High (4)

#### leanness-1 — Folded-state section is ceremony on the agent load path

- Lens: leanness
- Location: `references/room-event-contract.md:Folded state`
- Evidence: SKILL.md loads this file only for the no-script hand-append path; Folded state describes how the room derives state and does not change which fields an agent writes.
- Recommendation: Keep Storage, Event envelope, and Event types on the agent path; leave Folded state for the room app.
- Proposed smallest: Omit '## Folded state' from the agent-loaded contract.
- Predicted delta: Nothing for correct hand-written events. Route to variant eval to confirm.

#### determinism-1 — Resolve allows transitions out of terminal item statuses

- Lens: determinism
- Location: `scripts/room_signal.py:cmd_resolve`
- Evidence: After done/failed/answered/rejected, operator decisions are accepted again (e.g. done→approved exits 0), resurrecting closed items.
- Recommendation: Reject resolves from terminal statuses; add unit tests.

#### determinism-2 — Risks folded by bare risk id, not project-scoped

- Lens: determinism
- Location: `scripts/room_signal.py:fold`
- Evidence: risks[risk] overwrites globally; two projects using the same stable id lose one blocker from state, evaluate, and health.
- Recommendation: Key risks as project|risk; add a two-project unit test.

#### enhancement-1 — Add plan-validate-execute to approval execution

- Lens: enhancement
- Location: `SKILL.md:Executing approvals`
- Evidence: Fetch → post → resolve with no re-check; an operator reject/edit landing between fetch and post would be ignored on an irreversible external write.
- Recommendation: Plan ready items and payloads; immediately before each post re-read the item and abort unless still approved/edited with the same payload; then post and resolve.

### Medium (3)

#### leanness-2 — Live-push API docs invite work the fallback forbids

- Lens: leanness
- Location: `references/room-event-contract.md:Live push`
- Evidence: The fallback is append-only, but the same reader is taught the POST shape, which can prompt a DIY push without the script's failure handling.
- Recommendation: Omit Live push from the agent-loaded write contract; keep it for the room app.
- Proposed smallest: Omit '## Live push' from the agent-loaded contract.
- Predicted delta: Agents without the script would not POST, which is correct. Route to variant eval to confirm.

#### determinism-3 — Fire --clear without matching --ref silently no-ops while ok:true

- Lens: determinism
- Location: `scripts/room_signal.py:cmd_fire`
- Evidence: Clearing a fire raised with --ref but cleared without it returns ok:true, recorded:false; the pod stays red.
- Recommendation: Exit 1 when --clear matches no active fire and list the active refs for that project/reason; add a unit test.

#### enhancement-2 — Tighten graceful degradation for fire hand-writes

- Lens: enhancement
- Location: `SKILL.md:When the script can't run`
- Evidence: The fallback skips dedup entirely, so a hand-written fire can re-alert Slack.
- Recommendation: For fire only, scan existing events for an active same project|reason|ref before appending.
