---
name: brief
description: Write and post the 08:30 morning brief across every active project
code: MB
added: 2026-10-16
type: prompt
---

# Morning Brief

## What Success Looks Like

By 08:35 the operator reads one Slack message on their phone and knows what needs them today, in order, and why. Every active project appears: a stand-up line, or a clear "no stand-up". Every open approval and ask is in it with its id, so they can answer in the thread. Nothing is said twice, and a quiet project is never reported as fine.

## Your Approach

Set your room status to `meeting` with the task "Morning brief". The PMs' stand-ups put them at your desk.

**Read the score.** Build from the portfolio wake printed (each project's stand-up, last wrap, inbox, and silence), aor-signal `state` (open items, active fires, project health), `routing.md`, and the Unsorted lines. Read `briefs/` from the last two days for what you already said. Don't open the sources yourself; the stand-ups did that.

**Chase the silent.** For each project in `MISSING STAND-UPS`, check aor-signal for that PM's latest status. If the PM is mid-stand-up, wait a few minutes once and re-read. Otherwise the brief says "no stand-up" with the last activity time, and you add a `maestro` inbox item to that project ("Stand-up missing on <date>", `--key standup-missing|<date>`) so its PM sees it next run. A project in `SILENT PROJECTS` is off-tempo even if it has a stand-up.

**Write it in this order, leaving out empty sections, in the shape BOND asks for:**

1. **Your cue:** every open approval and ask, grouped by project, with id, one-line preview, and how long it has waited. Lead with the one that unblocks the most.
2. **Fires:** active fires, with who is on each and what happens next.
3. **Off-tempo:** missing stand-ups, silent projects, items past their cue in a stand-up's Holding or Unstaffed lines, and cross-project patterns you heard.
4. **To-dos:** what the operator personally does today that isn't an approval: meetings to prepare, answers promised. Only from stand-ups, BOND, and MEMORY.
5. **Unsorted:** intake you couldn't place, one line each, asking which project.
6. **In time:** one line naming the projects that need nothing.

Close with the reply commands (`approve all`, `approve <id>`, `reject <id>: reason`, `edit <id>: text`, `answer <id>: text`) and a link to the room (`aor_room_url`) when items are listed.

**Post it.** Save it to `briefs/<local date>.md` first. Then run `scripts/slack_post.py --root {project-root} --text-file <that file>`. If it returns `"fallback": "slack-mcp"`, post the same text through the Slack MCP to the operator channel and add one line at the end: "Posted as you, so no notification; add the Maestro bot token to get pinged." Write the returned `ts` at the top of the brief file as `thread_ts: <ts>`. Relay digests reply in that thread.

**Record it.** Every approval and ask the brief listed counts as digested: run aor-signal `digest --mark-sent <ids> --channel <channel> --thread-ts <ts>`. Fires the brief alerted that were in `fires_to_alert` go in the same call with `--mark-alerted <keys>`. Only after the post succeeded.

**Tend your files.** Rewrite `portfolio.md` with one line per active project (tempo, what it waits on, since when). Apply any routing the operator gave in yesterday's threads to `routing.md`. Log `[maestro] brief posted` with the Slack link in every project you added an item to. Set your status back to `idle`.
