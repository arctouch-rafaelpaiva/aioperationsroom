---
name: post-approved
description: Post exactly what the operator approved for this member on this project (Figma comments and replies, Jira comments, Slack messages), then record the result
code: PA
added: 2026-10-16
type: prompt
---

# Post Approved

## What Success Looks Like

Every approved item of yours on this project is posted exactly as approved, once, and has a `done` with the result link or a `failed` with a note. Nothing unapproved is posted.

## Your Approach

Follow aor-signal's plan, validate, and execute steps for items with `--owner <member id> --project <id>`. Post the `final_payload` if the operator edited it, otherwise the `payload`. Re-read each item right before posting.

- **Figma `comment`:** one comment pinned to the `target_url` frame (or a reply in the thread the item names), through the Figma MCP or `figma_states.py comment` (`references/figma-access.md`).
- **Jira `comment`:** one comment on the `target_url` issue, through the Jira tool (Atlassian MCP).
- **Slack `post_message`:** one message where `target_url` points, through the Slack MCP.
- **Notion `update_page`:** append the approved content to the `target_url` page; never rewrite what's there.

If the tool for an item isn't connected in this run, post nothing, leave it approved, and hand back `status: blocked` naming the tool. Log `[design] posted <item>: <result link>`, and end with the hand-back block.
