---
name: draft-stories
description: Turn an opportunity, brief, or request into an epic and ready, testable stories, and raise one hand to create them in Jira
code: DS
added: 2026-10-16
type: prompt
---

# Draft Stories

## What Success Looks Like

A draft in `outputs/requirements/` that the team could refine in one pass: each story has a clear who and why, AC a tester can run, the rules written down, the edge cases named, the dependencies linked, and the unknowns stated as open questions with owners. `scripts/stories.py check` passes with no errors. If the work should go into Jira, there is exactly one approval for the whole batch, and its payload is exactly what `stories.py payload` produced.

## Your Approach

Set your room status to `reading` with the cue in one line.

**Measure first.** Read the cue's inputs and what already exists: the Jira epic and its stories (search the project for the topic, so you never draft a duplicate), discovery's outputs, the Notion page, and the Figma link. Note what each source says and where they disagree. If the backlog already holds the story, switch to a readiness review of it and say so in the hand-back.

**Cut.** Set your status to `drafting`. Write the draft to `outputs/requirements/<YYYY-MM-DD>-<slug>.md` in the shape of `references/story-format.md`, in the AC format and language BOND names (Given/When/Then and the operator's language until First Breath says otherwise). Split by the team's preference in BOND; by default, one user-visible outcome per story. Every rule you couldn't confirm goes under Open questions with an owner, never into the AC as a guess. Where a story needs a design state that Figma doesn't show, add it as a dependency on design.

**Check.** Run `uv run scripts/stories.py check --file <draft>`. Fix every error. Treat each warning as a question: fix it or keep it on purpose.

**Raise your hand**, unless the cue said drafts only or the Jira tool isn't connected. Run `stories.py payload --file <draft> --out <draft>.payload.json`, then aor-signal `approval --project <id> --agent <member id> --target jira --action create_issues --preview "<its preview>" --rationale "<why now; how many stories are not ready and why>" --payload-file <draft>.payload.json`. One approval per draft, never one per story.

**Log and hand back.** Log `[requirements] drafted <n> stories for <topic>` with the draft path. Questions only the operator can answer become at most one aor-signal ask; the rest go into the hand-back with owners. Set your status to `idle` and end with the contract's hand-back block.
