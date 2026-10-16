---
name: contradiction-check
description: Compare what the docs, tickets, designs, and code say about one subject, and report every disagreement with both sources and the proposed correction
code: CX
added: 2026-10-16
type: prompt
---

# Contradiction Check

## What Success Looks Like

For the subject in the cue (a feature, an epic, a rule like "refund window"), every place the project states it has been read, and every disagreement is listed with the exact text and link on each side. Each one says which side wins by BOND's source order or by a later recorded decision, and the correction to draft, or, when no rule settles it, the question for the owner. When everything agrees, the report says so in one line.

## Your Approach

Set your room status to `reading`. Collect every statement of the subject:

- **Decisions:** the project's `decisions.md` and the Notion decision log.
- **Docs:** the PRD and specs in `sources.notion` (Notion MCP).
- **Tickets:** the stories and their AC in Jira.
- **Designs:** frames and their copy (`references/figma-access.md`).
- **Code:** when the subject is a rule the code enforces, the implementation (`references/code-access.md`): a constant, a validation, a message.

Pull the claims out as short facts with their source and date ("refund window: 30 days — PRD §Policy, edited Oct 2"). Compare facts on the same point. Wording that differs but means the same isn't a finding; terms are the glossary-check's job.

For each disagreement, apply BOND's source order and look for a later decision that settles it. If a rule settles it, the losing sources get a drafted correction. If not, write the question for the owner, with both texts.

**Write and raise.** Write `outputs/docs/<YYYY-MM-DD>-contradictions-<slug>.md`: a summary line, then one entry per disagreement (the point, each side with text, link, and date, the ruling or the question, the correction). Raise one aor-signal approval per correction on its own target: a Jira comment on the story, a Notion comment on the page, or a Figma comment on the frame. A contradiction in code goes to engineering in `follow_ups`, never as a code change.

**Log and hand back.** Log `[docs] contradictions <slug>: <n> found, <c> corrections drafted`. Set your status to `idle`, and end with the hand-back block; unsettled ones go in `questions` with their owners.
