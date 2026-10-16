# Pulse

**Default frequency:** Two Cursor automations: `brief` at 08:30 operator time on weekdays (after the PMs' stand-ups), and `relay` every 30 minutes, every day.

Relay runs every 30 minutes and may overlap a brief, so a pulse writes only its own session log, its own `unsorted/<local date>/<run id>.md`, project inboxes and daily logs through aor-agent-pm's `project_memory.py`, and room events through aor-signal. Only the brief run (wake prints `SANCTUM CURATOR: yes`) edits `briefs/`, `portfolio.md`, `routing.md`, and the core sanctum files (MEMORY, BOND, PERSONA, CREED, INDEX). Outside a pulse, they change only in a chat with your owner.

## Every pulse, in order

1. **Clock in.** Use the automation's run id as `AOR_RUN_ID` for every script call. Set your room status through aor-signal (`--project room --agent aor-agent-maestro`, `reading`, with the task in one line).
2. **Calibration.** If wake printed `CALIBRATION: pending`, you are running on seed defaults. Check aor-signal for an open ask of yours that asks the operator to talk to you once. Raise it only if none is open, and keep working.
3. **The task.** Run the row for `TASK` below.
4. **Curate the sanctum, curator only.** If wake printed `SANCTUM CURATOR: yes`, load `references/memory-guidance.md` and distill the last day's session logs into MEMORY.md, keeping it near or under 1500 tokens. Update INDEX.md if new organic files appeared, and BOND.md if something about the owner changed. Prune session logs older than 14 days and `unsorted/` days older than the last brief once their value is captured.
5. **Clock out.** Write your session log (`sessions/<local date>/<run id>.md`). Set your status to `idle`, then run aor-agent-pm's `project_memory.py sync --sanctum aor-agent-maestro` with one `--project` per project whose inbox or daily log you wrote, and a one-line message. If sync reports a conflict, your commit is still local. Run `git pull --rebase`; for each listed file, keep the incoming version and re-apply only your edit; then run `git rebase --continue` and sync again. If that fails too, say so in the next digest, naming the files.

## Task Routing

| Task | Action |
|------|--------|
| `brief` | Load `references/brief.md` |
| `relay` | Load `references/relay.md`; its intake step loads `references/comms-intake.md` |
| _(none)_ | Steps 1–2 and 5 only, with a one-line status |

## Quiet Hours

Quiet hours (`aor_quiet_hours`) never stop a run and never hold a fire alert. They hold digests: aor-signal's `digest` returns `send: false` during quiet hours, and pending items wait for the first relay after them.

## Self-Improvement

In your session log, note what fell flat this run: a brief line the operator ignored, an email you couldn't place, a digest reply you couldn't parse. Curation turns repeated notes into lessons in MEMORY.md.
