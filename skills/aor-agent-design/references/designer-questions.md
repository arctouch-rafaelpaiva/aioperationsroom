---
name: designer-questions
description: Collect open questions from Figma comments and design threads, answer what the story or a decision already settles, and route the rest to their owners
code: DQ
added: 2026-10-16
type: prompt
---

# Designer Questions

## What Success Looks Like

No designer's question sits unanswered for days. Every open question in the project's Figma comments and design threads since the last run is listed with its frame, and is either answered from a source (with the quote and link, waiting for approval) or routed to its owner as a precise question. Questions already answered in the thread are left alone.

## Your Approach

Set your room status to `reading`. Collect unresolved comments from each `sources.figma` file (`references/figma-access.md`; `figma_states.py comments --url <file>`) and design questions from the cue (Slack threads, Jira comments). Skip comments that aren't questions, that already have an answer in their thread, or that you listed in your last `outputs/design/*-questions.md` without anything new.

For each question, read the frame and the story it belongs to, then the sources: the story and AC, requirements' outputs, the design system in BOND, and the project's `decisions.md`.

- **Settled by a source:** draft the reply quoting the source with its link.
- **Not settled:** write the question for its owner (product questions to requirements or the client contact through the PM, technical feasibility to engineering, system questions to the design-system owner in BOND), with the options and what each means for the design.

Write `outputs/design/<YYYY-MM-DD>-questions.md` with every question, its frame link, and its answer or owner. Raise one aor-signal approval per reply you drafted (`--target figma --action comment --target-url <frame link>`, as a reply in that thread). Questions for squad members go in the hand-back's `questions` with their owners; questions for the client go to the PM in `follow_ups`.

Log `[design] questions: <n> open, <a> answered, <r> routed`, set your status to `idle`, and end with the hand-back block.
