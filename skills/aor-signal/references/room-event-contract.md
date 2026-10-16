# Room Event Contract (v1)

This is the wire and storage format shared by `scripts/room_signal.py`, the AI Operations Room web app (Vercel), and any agent writing events by hand when the script can't run. Writers need only **Storage**, **Event envelope**, and **Event types**. **Room app only** covers the live push and how the room folds state. A change to this file is a schema version bump.

## Storage

- Path: `{ops-repo}/aor/room/events/<YYYY-MM-DD UTC>/<run-id>.jsonl`. Use one file per run (or per room/Slack writer), so concurrent writers never touch the same file.
- One JSON object per line. Append only; never rewrite a line.
- The room app writes the operator's room actions the same way: one file per write, e.g. `room-<uuid>.jsonl`, committed through the GitHub API.

## Event envelope

| Field | Type | Notes |
|---|---|---|
| `v` | int | Schema version, `1` |
| `id` | string | Unique. Asks are `q-…`, approvals are `ap-…`, everything else is `ev-…` |
| `ts` | string | UTC ISO-8601 with milliseconds, e.g. `2026-10-15T12:00:00.123Z` |
| `type` | string | See the event types below |
| `project` | string \| null | Project id; null only for `digest_sent` |
| `agent` | string \| null | Acting skill (`aor-agent-qa`), or `room` / `slack` / `operator` for operator actions |
| `run` | string | Writer's run id |
| `data` | object | Type-specific fields |

## Event types (`data`)

| Type | Data | Effect |
|---|---|---|
| `status` | `status` (`idle` \| `working` \| `reading` \| `drafting` \| `meeting` \| `wrapping` \| `offline`), `task`, `source_url?` | Replaces the agent's current status. Drives the character's animation |
| `ask` | `question`, `options?[]`, `context_url?` | Opens a needs-you item with id = event id (speech bubble) |
| `approval` | `target` (`jira` \| `notion` \| `github` \| `figma` \| `slack`), `action`, `payload`, `preview`, `rationale`, `target_url?` | Opens an approval item with id = event id (raised hand on the `agent` character) |
| `resolve` | `item`, `decision`, `by`, `answer?`, `payload?` (edited content), `note?`, `result_url?` | Moves the item along its allowed transitions (below) |
| `risk_open` | `risk`, `title`, `kind` (`blocker` \| `risk`), `severity`, `ref?` | Opens a risk. Its identity is `project\|risk`, so ids may repeat across projects. `opened_at` = `ts` |
| `risk_close` | `risk` | Closes that project's risk |
| `fire` | `reason` (`failed_build` \| `missed_deadline` \| `client_escalation` \| `blocker_overdue` \| `other`), `detail`, `ref?` | Activates the fire with key `project\|reason\|ref`. Don't write one while the same key is active |
| `fire_clear` | `reason`, `ref?` | Deactivates the fire with the same key, so the ref must match |
| `digest_sent` | `items[]`, `fires?[]` (fire keys), `channel`, `thread_ts?` | Marks items as included in a Slack digest, and fires as alerted. Only a digest with `items` restarts the batch window |

**Resolve transitions.** Anything not listed here is invalid.

| Item | From | Allowed decisions |
|---|---|---|
| ask | `open` | `answered`, `rejected` |
| approval | `open` | `approved`, `edited` (with `payload`), `rejected` |
| approval | `approved` / `edited` | the agent posts, then records `done` or `failed`; the operator may still choose `edited` or `rejected` |

`answered`, `rejected`, `done`, and `failed` are final.

## Room app only

### Live push

- `POST {AOR_ROOM_URL}/api/events`
- Header: `Authorization: Bearer {AOR_ROOM_TOKEN}`
- Body: `{"events": [<event>, ...]}`
- The room de-duplicates by `id`, so replays from git are safe. A 2xx response means the event was accepted. Any failure is retried only through git reconciliation.

### Folded state (what the room renders)

- **Ordering:** stable sort by `ts`. A `resolve` whose item hasn't appeared yet is held and applied when the item arrives.
- **Agents:** the latest `status` per `project/agent`. The project id `room` is reserved for Maestro's own desk (status and asks from `aor-agent-maestro`); it is never a pod, and the room renders its status and items at Maestro's desk.
- **Items:** asks and approvals with their current status. `final_payload` holds the latest edited content.
- **Risks:** keyed `project|risk`, open or closed, with `opened_at` and `closed_at`.
- **Fires:** keyed `project|reason|ref`, active or cleared, with `alerted_at` once Maestro has alerted that activation.
- **Project health:**
  - `red` if any fire is active.
  - Otherwise `amber` if any ask or approval is `open`.
  - Otherwise `green`.
  - Also reports counts of `needs_you` and `approvals`.
