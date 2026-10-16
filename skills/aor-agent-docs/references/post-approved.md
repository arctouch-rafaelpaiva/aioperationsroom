---
name: post-approved
description: Post or edit exactly what the operator approved for this member on this project (Notion updates and comments, Jira and Figma comments, Slack messages), then record the result
code: PA
added: 2026-10-16
type: prompt
---

# Post Approved

## What Success Looks Like

Every approved item of yours on this project is applied exactly as approved, once, and has a `done` with the result link or a `failed` with a note. Nothing unapproved is posted or edited.

## Your Approach

Follow aor-signal's plan, validate, and execute steps for items with `--owner <member id> --project <id>`. Use the `final_payload` if the operator edited it, otherwise the `payload`. Re-read each item and the target page right before applying it.

- **Notion `update_page`:** apply only what the payload names, through the Notion MCP. For an append (a decision log entry, glossary terms, release notes), add it at the end of the named section. For section replacements (prd-update), replace each named section's text with the approved text, and only if the section still reads as the draft quoted; if it changed since, apply nothing and mark the item `failed` with "page changed since the draft".
- **Notion `comment`:** one comment on the `target_url` page.
- **Jira `comment`:** one comment on the `target_url` issue, through the Jira tool (Atlassian MCP).
- **Figma `comment`:** one comment on the `target_url` frame (`references/figma-access.md`).
- **Slack `post_message`:** one message where `target_url` points, through the Slack MCP.

If the tool for an item isn't connected in this run, apply nothing, leave it approved, and hand back `status: blocked` naming the tool. Log `[docs] applied <item>: <result link>`, and end with the hand-back block.
