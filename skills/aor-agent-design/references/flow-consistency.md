---
name: flow-consistency
description: Walk a flow across its frames and flag inconsistent words, patterns, and dead ends, so the same action looks and reads the same everywhere
code: FC
added: 2026-10-16
type: prompt
---

# Flow Consistency

## What Success Looks Like

For the flow in the cue (a feature, an epic, or a Figma page), every inconsistency that would confuse a user is listed with the frames on both sides: two names for one action, one pattern drawn two ways, a step with no way back or forward, copy that contradicts the story or the design system. Each one ends in a question with the options, not a redesign.

## Your Approach

Set your room status to `reading`. Read the frames in flow order (prototype connections when they exist, otherwise the page order and the story's steps) through `references/figma-access.md`. Keep BOND's design system and product words at hand.

Walk it as a user would, start to finish, and then once more for each error path. Note:

- **Words:** the same thing named differently (Cancel or Void, Refund or Return), labels that differ from the story's terms, tone that shifts.
- **Patterns:** the same action drawn with different components, placements, or confirmation behavior; components that aren't in the system.
- **Paths:** dead ends, steps without back or cancel, an error with no recovery, a success with nowhere to go.
- **Story fit:** steps the story needs that aren't drawn, or steps drawn that no story asks for.

Write `outputs/design/<YYYY-MM-DD>-flow-<slug>.md`: the flow in one line per step with frame links, then the findings grouped as above, each with both frames and the question ("Same action? If yes, which word?"). Raise one aor-signal approval for a Figma comment on the flow's first frame with the list, or, when BOND says designers want questions in Slack, one `--target slack` message to the project channel. Steps no story asks for go to the PM in `follow_ups`.

Log `[design] flow <slug>: <n> findings`, set your status to `idle`, and end with the hand-back block.
