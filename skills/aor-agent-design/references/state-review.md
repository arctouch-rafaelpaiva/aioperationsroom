---
name: state-review
description: Review a story's designs for every state it needs (default, loading, empty, error, success, and the story's own cases) and for accessibility, with one drafted list of questions
code: SR
added: 2026-10-16
type: prompt
---

# State Review

## What Success Looks Like

For the story in the cue, `outputs/design/<YYYY-MM-DD>-states-<story key>.md` shows each screen the story touches, which states are drawn (with frame links), which are missing, and the accessibility questions that matter. The designer gets one comment with the missing states and the questions, waiting for approval. Work that holds is credited by name.

## Your Approach

Set your room status to `reading`. Read the story with its AC and rules, plus requirements' and QA's outputs for it when they exist. Find its designs: Figma links in the story, then the project's `sources.figma` files (`references/figma-access.md`). If BOND marks the file or page as work in progress, review only if the cue asks.

**Write the state spec.** List each screen the story touches and the states it needs: the standard ones that apply (default, loading, empty, error, success, disabled, offline), plus every case the story names (an AC like "over the limit" is a state). Write it as `outputs/design/<YYYY-MM-DD>-states-<story key>.yaml` in the shape the script's `--help` shows, using `match:` with BOND's frame names when they differ from the screen name.

**Check.** Get the frame list (Figma MCP, or `figma_states.py frames --url <file>`) as JSON and run `uv run scripts/figma_states.py check --spec <yaml> --frames <json>`. The script decides drawn or missing from frame names; open the frames it found and confirm by looking: a frame called "Error" that shows a generic toast for a payment failure is a finding. Unclaimed frames may be states with unusual names; look before calling a state missing.

**Accessibility.** On the frames you opened, ask what BOND's bar requires: contrast of text and controls, labels for icons and fields, color never alone, focus order and visible focus, touch targets, text that grows, motion. Ask questions; don't assert failures you can't measure.

**Write and raise.** Write the review: the plain summary, the per-screen table (drawn with links, missing), the visual findings, the accessibility questions, and what works. Raise one aor-signal `approval --target figma --action comment --target-url <the main frame link>` whose payload is the comment: the missing states and the questions as one short list, each naming its frame. Missing cases that are really gaps in the story go to requirements in the hand-back's `questions`.

**Log and hand back.** Log `[design] <story>: <missing> states missing, <q> a11y questions`. Set your status to `idle`, and end with the hand-back block.
