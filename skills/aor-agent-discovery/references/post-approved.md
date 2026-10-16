---
name: post-approved
description: Post exactly what the operator approved for this member on this project (Notion research pages, Slack messages, Jira comments), then record the result
code: PA
added: 2026-10-16
type: prompt
---

# Post Approved

## What Success Looks Like

Every approved item of yours on this project is posted exactly as approved, once, and has a `done` with the result link or a `failed` with a note. Nothing unapproved is posted.

## Your Approach

Follow aor-signal's plan, validate, and execute steps for items with `--owner <member id> --project <id>`. Use the `final_payload` if the operator edited it, otherwise the `payload`. Re-read each item right before posting.

- **Notion `update_page`:** append the approved brief or report to the `target_url` page through the Notion MCP; never rewrite what's there.
- **Slack `post_message`:** one message where `target_url` points, through the Slack MCP. Never a message to a user, client, or stakeholder directly.
- **Jira `comment`:** one comment on the `target_url` issue, through the Jira tool (Atlassian MCP).

Before posting, check the payload once more for names, emails, or phone numbers of end users; if any slipped in, post nothing and mark the item `failed` with "contains personal data". If the tool for an item isn't connected in this run, post nothing, leave it approved, and hand back `status: blocked` naming the tool. Log `[discovery] posted <item>: <result link>`, and end with the hand-back block.
