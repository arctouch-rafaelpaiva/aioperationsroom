---
name: post-approved
description: Post exactly what the operator approved for this member on this project (PR comments, Jira comments, Slack replies), then record the result
code: PA
added: 2026-10-16
type: prompt
---

# Post Approved

## What Success Looks Like

Every approved item of yours on this project is posted exactly as approved, once, and has a `done` with the result link or a `failed` with a note. Nothing unapproved is posted.

## Your Approach

Follow aor-signal's plan, validate, and execute steps for items with `--owner <member id> --project <id>`. Post the `final_payload` if the operator edited it, otherwise the `payload`. Re-read each item right before posting.

- **GitHub `comment`:** one comment on the `target_url` PR or issue, through the GitHub tool (`references/code-access.md`). A comment, never a review that approves or requests changes, and never a code suggestion block unless the approved text has one.
- **Jira `comment`:** one comment on the `target_url` issue, through the Jira tool (Atlassian MCP).
- **Slack `post_message`:** one reply or message where `target_url` points, through the Slack MCP.

If the tool for an item isn't connected in this run, post nothing, leave it approved, and hand back `status: blocked` naming the tool. Log `[eng] posted <item>: <result link>`, and end with the hand-back block.
