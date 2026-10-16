---
name: aor-onboard-project
description: Registers AI Operations Room projects and agents. Use when the operator wants to 'add a project to the room', 'onboard project X', 'change a project's sources', 'add an agent to a pod', 'archive a project', or when a PM must validate its project.yaml.
---

# aor-onboard-project

This skill keeps the AI Operations Room's project registry: one `project.yaml` per project, plus that project's memory folder. Act as the room's registrar. You get from the operator exactly where a team's work lives, and you check each source against the connected tools before anything is written. `scripts/project_registry.py` owns the file format, validation, memory scaffold, and automation checklist. Three readers set the bar:

- **The PM and specialists** read `project.yaml` on every run to know where to look. A source that is vague ("the payments board") or wrong sends every run to the wrong place, silently. Each source must be an exact id or URL that has been opened through its tool.
- **The room** draws one pod per active project from this file.
- **The operator** creates the Cursor automations from the checklist, so it must be copy-ready.

Run `uv run scripts/project_registry.py --help` (and `<command> --help`) for the exact interface. Every command prints JSON, and exit 1 means the request was invalid, with a message naming the fix. Mutating commands return `changed` (paths to commit), `warnings`, and `room_signals`.

## Resolution rules

- Bare paths (e.g. `scripts/project_registry.py`) resolve from this skill's installed directory.
- `{project-root}` → the ops repo checkout (`aor-ops`). Pass it as `--root` when the working directory differs.
- `aor-signal` → the sibling skill that writes room state. Run each `room_signals` entry as `uv run <aor-signal>/scripts/room_signal.py <entry…>`.

## Intents

| The operator wants | Command |
|---|---|
| A new project in the room | `onboard --spec -` |
| Different Notion, Jira, Figma, GitHub, or Slack sources | `update-sources --project <id> --spec -` |
| A new agent in a pod (standard role, or a custom agent `--based-on` a specialist skill) | `add-agent` |
| A project out of the room, or back in | `archive [--restore]` |
| A check of `project.yaml` (PM first run, after a room-wizard commit, after a hand edit) | `validate --project <id> --scaffold` or `validate --all` |
| The automation list again | `checklist --project <id>` |

## Onboarding a project

Gather the name and the sources, then the roster and fire threshold. Offer the defaults for the last two: the PM plus all six specialists, and the module's 24h blocker threshold. Ask source type by source type, because the operator usually remembers them one system at a time. Each answer becomes the `sources` shape that `onboard --help` names:

- **Notion:** the workspace, teamspace, or the root pages and databases the team treats as truth.
- **Jira:** the site, the project keys, and the boards, or a JQL scope when the work cuts across projects.
- **Figma:** team, project, or file URLs.
- **GitHub:** `owner/repo` for each repo.
- **Slack:** each project channel, and whether it is for `context` (the PM reads it), `post` (agents post there after approval), or both.

**Check every source through its connected tool before writing.** Turn names into ids: search Slack for the channel id, look up the Jira key and board, and open the Notion page, the Figma file, and the repo. A source you opened gets `verified: <today>`. If the tool isn't connected in this run, record the source as given with `verified: false`, and tell the operator which tool to connect. Don't stop the onboarding for it.

Then show the operator the whole spec in plain words: name, id, every source, roster, threshold. The id is permanent, so get a yes before running `onboard`. Pass the spec as JSON on stdin.

After it succeeds:

1. Set `AOR_RUN_ID` and run each `room_signals` entry through `aor-signal`, so the characters arrive in the room now instead of at the next git sync.
2. Commit `changed` and `aor/room/` together, once, and push.
3. Show the checklist and ask the operator to create those automations. The project does nothing on its own until they exist.
4. Repeat any warnings, such as unverified sources.

## The other intents

- **Update sources.** Each source type you pass is replaced whole, and `null` removes it. So read the current `project.yaml` first, then pass the complete new list for that type. Check new sources the same way as at onboarding. The checklist is regenerated; point out any automation the operator must add or remove.
- **Add agent.** A custom agent needs a name, the specialist skill it runs on, and persona notes that say how it differs from that skill. Signal, commit, and push as at onboarding.
- **Archive.** Confirm first. Archiving keeps every file in place and is reversible with `--restore`. Signal everyone `offline`, commit, and tell the operator to disable the project's automations.
- **Validate.** This is the PM's first-run check, and it runs headless. If it fails, don't repair `project.yaml` yourself. Raise an `aor-signal` ask that quotes the errors, because the fix is the operator's call. Commit any files `--scaffold` created.

## Gotchas

- **Never test a Slack channel or any target by posting to it.** Every external post needs an approved raised hand. Reading is enough to verify.
- **Store channel ids, not `#names`.** Names change, and the script rejects anything that doesn't look like an id.
- **Ids never change.** Renaming the display name is fine. A different id means archiving this project and onboarding a new one.
- **No secrets in `project.yaml`.** It sits in git and the room reads it. Tokens belong in the automation and Vercel environment.
- **The script never commits**, and it never calls `aor-signal`. Unsignalled characters appear only after the next git sync, and an uncommitted file never reaches the room.
- **Without Python or `uv`**, stop and say so. Point the operator to the room's onboarding wizard instead. Don't hand-write `project.yaml`: every agent and the room trust it to be valid.
