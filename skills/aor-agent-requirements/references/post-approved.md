---
name: post-approved
description: Post exactly what the operator approved for this member on this project (Jira issues and comments), then record the result
code: PA
added: 2026-10-16
type: prompt
---

# Post Approved

## What Success Looks Like

Every approved item of yours on this project is posted exactly as approved, once, and has a `done` with the result link or a `failed` with a note. Nothing unapproved is posted.

## Your Approach

Follow aor-signal's plan, validate, and execute steps for items with `--owner <member id> --project <id>`. Post the `final_payload` if the operator edited it, otherwise the `payload`. Re-read each item right before posting.

- **`create_issues`:** create the epic first unless `epic.key` is set, then each story in order, in `project_key`, with the given summary, description (markdown), and labels, linked to the epic. If a story fails partway, stop, resolve `failed` with a note listing what was created (keys) and what wasn't, and never retry blindly; the next attempt needs a new approval for the rest.
- **`comment`:** one comment on the `target_url` issue, with the payload as its body.

Use the connected Jira tool (the Atlassian MCP). If it isn't connected in this run, post nothing, leave the item approved, and say so in the hand-back with `status: blocked`.

Log `[requirements] posted <item>: <result link>`, and add the created keys to the draft file's frontmatter (`created: PAY-150, PAY-151`) so the next run knows they exist. End with the hand-back block.
