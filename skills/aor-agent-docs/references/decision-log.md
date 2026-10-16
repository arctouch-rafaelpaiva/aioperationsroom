---
name: decision-log
description: Capture a decision from a thread, meeting, or comment with who, when, why, and what it supersedes, and hand it back for the project's decision record
code: DL
added: 2026-10-16
type: prompt
---

# Decision Log

## What Success Looks Like

Each decision in the cue is written once, faithfully: what was decided, who decided it, when, why, the link to where it happened, and the earlier decision it replaces. It reaches the project's `decisions.md` through the PM, and the Notion decision log when BOND names one. Every document the decision changes is listed, so nothing keeps the old answer.

## Your Approach

Set your room status to `reading`. Read the source in the cue (a Slack thread, meeting notes, a Jira or Figma comment) to the end: decisions get revised in the replies. A decision is a settled choice by someone who can make it; a suggestion, a question, or "let's think about it" isn't one. When it's unclear whether it's settled, it goes to the hand-back as a question for the person who'd decide.

**Check what it replaces.** Search the project's `decisions.md`, your recent outputs, and the Notion decision log for earlier decisions on the same subject.

**Write it.** Write `outputs/docs/<YYYY-MM-DD>-decision-<slug>.md`: the decision in one sentence, why, who and when, the source link, what it supersedes, and the documents that now disagree with it (the PRD section, stories, designs) with links. Each of those becomes a follow-up (a PRD update or a correction), not a silent edit.

**Record it.** Put the decision in the hand-back's `decisions` field; the PM appends it to `decisions.md`. If BOND names a Notion decision log, raise one aor-signal `approval --target notion --action update_page --target-url <log page>` whose payload is the entry to append.

**Log and hand back.** Log `[docs] decision: <one line>`. Set your status to `idle`, and end with the hand-back block, with the documents to correct in `follow_ups`.
