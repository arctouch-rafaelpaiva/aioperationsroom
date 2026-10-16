# The room app

The wall view of the AI Operations Room. It draws a pixel-art office with Maestro's desk and one pod per active project, where each squad member sits at a desk and shows what they're doing. Fires turn a pod red. Anything that needs you (approvals and questions) collects in the **Waiting on you** tray, where you approve, edit, reject, or answer, one at a time or in bulk.

The app reads the same append-only event log the skills write (`aor/room/events/<date>/<run>.jsonl`) and folds it the same way as `skills/aor-signal/scripts/room_signal.py`. Your decisions are written back as `room-<uuid>.jsonl` runs, so the next PM run posts approved items just as it does for Slack replies.

## Run it locally

```bash
npm install
npm run dev        # http://127.0.0.1:4317
```

With no configuration it opens a **demo room** with three sample projects that changes every few seconds. Decisions there stay in memory.

To open your own room, point it at a checkout of the ops repo:

```bash
AOR_OPS_DIR=/path/to/ops-repo npm run dev
```

## Views

| URL | What you get |
|---|---|
| `/` | The room (or a list view on phones), with project and member panels and the approvals tray |
| `/?kiosk=1&token=<AOR_KIOSK_TOKEN>` | Full-screen, view-only wall display: a red, amber, or green footer, a hidden cursor, and night dimming during quiet hours |
| `/?kiosk=1&token=…&sound=1` | The kiosk with a short chime when a new fire starts |

## Configuration

| Variable | Purpose |
|---|---|
| `AOR_OPS_DIR` | Local ops-repo checkout to read and write (takes priority) |
| `AOR_GITHUB_REPO`, `AOR_GITHUB_TOKEN`, `AOR_GITHUB_BRANCH` | Read the ops repo through the GitHub API and commit decisions to it (`owner/name`, a token with contents read and write, branch defaults to `main`) |
| `AOR_OPERATOR_PASSWORD` | Required before anyone can act on a GitHub-backed room; without it, a GitHub-backed room is view-only |
| `AOR_SESSION_SECRET` | Signs the 14-day operator session cookie (falls back to the room token or the password) |
| `AOR_KIOSK_TOKEN` | Lets a wall display view the room without signing in |
| `AOR_ROOM_TOKEN` | Bearer token for `POST /api/events`; the same secret `aor-signal push` uses |
| `KV_REST_API_URL`, `KV_REST_API_TOKEN` (or `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`) | Optional Redis for live events, so they survive restarts and reach every server instance |

Room settings (timezone and quiet hours) come from the `aor` section of the ops repo's `_bmad/config.yaml`.

## API

| Route | Who | What |
|---|---|---|
| `GET /api/state` | Operator or kiosk | The folded room snapshot that the UI polls every 4 seconds |
| `POST /api/items/resolve` | Operator | `{"items":[{"id","decision","note?","payload?","answer?"}]}`; illegal transitions are refused per item |
| `POST /api/events` | `Bearer AOR_ROOM_TOKEN` | `{"events":[...]}` from `aor-signal push`, up to 200 per call; events are de-duplicated by id |
| `POST`, `DELETE /api/session` | Anyone | Sign in with the operator password, or sign out |

Live events from `/api/events` show at once and are dropped from the live store when the commit that contains them reaches the ops repo.

## Deploy on Vercel

1. Import the repository in Vercel and set the **Root Directory** to `room`.
2. Add `AOR_GITHUB_REPO`, `AOR_GITHUB_TOKEN`, `AOR_OPERATOR_PASSWORD`, `AOR_SESSION_SECRET`, `AOR_KIOSK_TOKEN`, and `AOR_ROOM_TOKEN` as environment variables.
3. Optionally add an Upstash Redis integration from the Vercel Marketplace; it sets the `KV_REST_API_*` variables.
4. Set `aor_room_url` in the ops repo's `_bmad/config.yaml` to the deployment URL, and add `AOR_ROOM_TOKEN` as a Cursor Cloud Agents secret so scheduled runs can push live events.

## Checks

```bash
npm test               # fold parity with room_signal.py (needs python3), resolve rules
npx tsc --noEmit
npx eslint .
```
