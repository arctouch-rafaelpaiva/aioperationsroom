---
name: release-notes
description: Draft release notes for each audience from what actually shipped (done stories and merged changes), in the team's format, without promising anything the code doesn't do
code: RN
added: 2026-10-16
type: prompt
---

# Release Notes

## What Success Looks Like

For the release in the cue, `outputs/docs/<YYYY-MM-DD>-release-notes-<name>.md` has one section per audience BOND names (customers, internal, client), each in its format and language. Every line traces to a done story or a merged change, and says what the reader can now do, not how it was built. Changes with no story, and stories that aren't actually merged, are flagged, not published.

## Your Approach

Set your room status to `reading`. List the release scope from Jira (the version or sprint) and what merged on the default branch for it: engineering's change digests in `outputs/engineering/`, or the merges themselves (`references/code-access.md`). Read QA's release verdict in `outputs/qa/` if there is one; a no-go means the notes are a draft for later, and say so.

**Match.** Pair each done story with its merged changes. A story marked done with nothing merged, or a merge with no story, goes under **Flagged**, never into the notes.

**Write.** Set your status to `drafting`. For each audience, group by what the reader cares about (new, improved, fixed), one line each in plain language, in the glossary's words. Customer notes leave out internal names, ticket keys, and anything behind a disabled feature flag. Internal notes keep the keys and links. Check each line against its story's AC: never promise more than the AC.

**Raise.** Raise one aor-signal approval per publishing place BOND names (a Notion release page with `update_page`, or the project Slack channel with `post_message`), with that audience's notes as the payload.

**Log and hand back.** Log `[docs] release notes <name>: <n> lines, <f> flagged`. Set your status to `idle`, and end with the hand-back block, with the flagged items in `follow_ups`.
