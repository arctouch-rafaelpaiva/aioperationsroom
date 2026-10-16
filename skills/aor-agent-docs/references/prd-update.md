---
name: prd-update
description: Draft the exact change a PRD or spec needs after a decision or a story change, section by section, for its owner to approve
code: PD
added: 2026-10-16
type: prompt
---

# PRD Update

## What Success Looks Like

The PRD says what the team decided. For each section the cue's change affects, the draft shows the current text, the proposed text, and why (the decision or story with its link). Nothing in the page changes until the owner and the operator approve; then only the approved text, in only the approved sections.

## Your Approach

Set your room status to `reading`. Read the trigger (a decision from the decision-log, a story change, a contradiction finding) and the PRD or spec page in Notion. Find every section the change touches, including the indirect ones: a changed rule often appears in the overview, the flows, the edge cases, and the glossary.

**Draft.** Set your status to `drafting`. Write `outputs/docs/<YYYY-MM-DD>-prd-<slug>.md` with one entry per section: the section heading, the current text quoted, the proposed text, and the reason with its link. Keep the document's voice and structure; change what the decision changes and nothing else.

**Raise.** If BOND names you an editor of this page, raise one aor-signal `approval --target notion --action update_page --target-url <page>` whose payload lists each section with its exact replacement text. Otherwise raise one approval for a Notion comment on the page with the draft, tagged for its owner. Either way, the item's preview names the sections.

**Log and hand back.** Log `[docs] PRD <page>: <n> sections drafted`. Set your status to `idle`, and end with the hand-back block.
