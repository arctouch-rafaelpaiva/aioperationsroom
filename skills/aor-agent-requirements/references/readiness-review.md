---
name: readiness-review
description: Check existing Jira stories against the team's Definition of Ready, and draft one suggested-AC comment per story that needs it
code: RR
added: 2026-10-16
type: prompt
---

# Readiness Review

## What Success Looks Like

For each story in the cue, a verdict the team trusts: ready, or not ready with the exact gaps and a drafted fix. The review lives in `outputs/requirements/<YYYY-MM-DD>-review-<slug>.md`. Stories that need changes have one Jira comment each waiting for approval. You never overwrite a description, and you never change a status, an assignee, or a sprint.

## Your Approach

Set your room status to `reading`. Read each story from Jira with its epic, linked issues, comments, attachments, and design links, plus the related outputs from discovery, design, and QA.

**Measure against the team's Definition of Ready** in BOND. Until First Breath sets one, use this default:

- A user-story line with a real who and why
- AC a tester can run, in the team's format, with no vague wording
- Business rules written down, or stated as open questions with owners
- Design linked, with the states the AC need (empty, loading, error, success)
- Dependencies linked, and none blocked without a plan
- Small enough for one sprint, by BOND's size rule
- No open question that changes the scope

**Write the review**, one section per story: the verdict, each gap with the evidence (quote the AC or name the missing state), and the fix: suggested AC rewritten in the team's format, the rule to confirm and with whom, or the split.

**Raise your hands.** For each not-ready story with a fix, one aor-signal `approval --target jira --action comment --target-url <story link>` whose payload is the exact comment: the gaps and the suggested AC, in the team's language, short enough to read in the ticket. Ready stories get no comment. When the cue covers many stories, say in each rationale how many others were reviewed, so Maestro's digest reads as one batch.

**Log and hand back.** Log `[requirements] reviewed <n> stories: <ready> ready, <not> not ready` with the review path. Gaps that belong to design or QA become follow-ups in the hand-back. Set your status to `idle`, then end with the hand-back block.
