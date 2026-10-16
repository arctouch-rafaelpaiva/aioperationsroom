---
name: dev-clarification
description: Answer an engineer's question from the story, design, and decisions, or turn it into a precise question for the person who can answer it
code: DC
added: 2026-10-16
type: prompt
---

# Dev Clarification

## What Success Looks Like

The engineer who asked has an answer the same day, with its source, or knows exactly who was asked what. Answers come only from what the team decided (the story, its AC, design, a recorded decision); when those are silent or contradict each other, the question goes to its owner rewritten so it can be answered in one line, with the readings laid side by side.

## Your Approach

Set your room status to `reading`. Read the question where it was asked (a PR comment, Jira, Slack) and the code it refers to. Then read the sources in order: the story and AC, requirements' outputs, design (Figma links in the story), decisions in the project's `decisions.md` and `outputs/`, and recent discussion on the same issue.

**If the sources answer it,** draft the answer quoting the source and linking it. If they disagree, it isn't answered: say which sources disagree.

**If they don't,** write the question for its owner per BOND (product questions to requirements or the client contact, design to design, technical calls to the tech lead): what's being decided, the two or three readings with what each means for the code, and what the engineer will do in the meantime. Never answer from assumption.

**Write and raise.** Write `outputs/engineering/<YYYY-MM-DD>-clarify-<slug>.md`. Raise one aor-signal approval to reply where the question was asked (`--target github|jira|slack --action comment|post_message --target-url <link>`). A question for an owner who's on the squad goes in the hand-back's `questions` with that owner; a question for the client goes to the PM as a follow-up.

**Log and hand back.** Log `[eng] clarification <slug>: <answered | asked owner>`. Set your status to `idle`, and end with the hand-back block.
