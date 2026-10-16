---
name: pr-read
description: Read a pull request or technical discussion, explain it in plain language, and flag every gap between the change and its story
code: PR
added: 2026-10-16
type: prompt
---

# PR Read

## What Success Looks Like

Anyone in the room can read the first paragraph of `outputs/engineering/<YYYY-MM-DD>-pr<number>.md` and know what the change does and whether it matches its story. Below that, every gap is named with the code location and the story line it contradicts: an AC the change doesn't implement, behavior that differs from a rule, or work no story covers. Gaps that need a decision become one drafted comment, waiting for approval. When the change matches, the read says so in one line.

## Your Approach

Set your room status to `reading`. Get the change per `references/code-access.md`: the PR from the cue, its diff against the default branch, its description and discussion when a GitHub tool is available. For a technical discussion (an issue, a Slack thread), read the thread and the code it refers to.

**Find the intent.** Find the linked story (Jira key in the title, branch, or description, per BOND's conventions) and read its AC and rules, plus requirements' and design's outputs for it when they exist. Without a story, the whole change is untracked scope: note it.

**Read the diff,** not the title. Summarize what changes in two or three plain sentences (what the user or system does differently), then the technical shape one level down (new tables, endpoints, flags, migrations). For each AC, decide: implemented (where), partly (what's missing), or not touched. Look for behavior the story contradicts and work beyond the story.

**Dependencies.** If the diff touches a manifest, run dependency-alerts on the same refs and include its finding.

**Write it.** Write the read, with the plain summary, the AC table, the gaps (each with file and line, and the story line), and the risks for QA (flows touched that need retesting). Gaps that need a decision get one aor-signal approval: `--target github --action comment --target-url <PR link>` for questions to the engineers, or `--target jira --action comment` on the story when the story should change. The comment asks about intent; it never prescribes code. Scope beyond the story also goes in the hand-back's `follow_ups` for the PM.

**Log and hand back.** Log `[eng] PR #<n>: <matches | n gaps>` with the read path. Set your status to `idle`, and end with the hand-back block; name QA in `follow_ups` when flows need retesting.
