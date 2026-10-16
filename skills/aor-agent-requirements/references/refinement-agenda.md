---
name: refinement-agenda
description: Prepare the next refinement session: which stories, in what order, and the questions each one needs answered by whom
code: RA
added: 2026-10-16
type: prompt
---

# Refinement Agenda

## What Success Looks Like

The team walks into refinement with `outputs/requirements/<YYYY-MM-DD>-refinement.md` and leaves with stories ready. The agenda fits the session, starts with what unblocks the next sprint, and turns every gap into a question with the person who can answer it, so no time is spent discovering problems in the room.

## Your Approach

Set your room status to `reading`. Find the candidates: the stories the cue names, or the top of the backlog that isn't ready yet, plus stories touched since the last refinement. Read your recent reviews and drafts first, so you don't review a story twice.

**Order** by what the next sprint needs, then by dependency (a story others wait on comes first), then by how much one answer unblocks.

**For each story**, one block: the link and title, the verdict in one line (from a fresh readiness check), the questions in the order to ask them, each with who answers it (product, design, engineering, a client contact), and the decision to record. Stories that are already ready go in a short "confirm and estimate" list at the end.

**Close** with a time plan if BOND gives the session length, and a list of what to send ahead so the right people come prepared.

Nothing here posts by itself. If the cue asks to share the agenda in a project Slack channel or a Notion page, raise one approval with the exact text. Log `[requirements] refinement agenda ready (<n> stories)`, set your status to `idle`, and end with the hand-back block.
