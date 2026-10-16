---
name: defect-triage
description: Turn a bug report into facts: reproduced or not, severity by the team's rubric, duplicates, the story and change it likely came from, and what's missing
code: DT
added: 2026-10-16
type: prompt
---

# Defect Triage

## What Success Looks Like

Every bug in the cue has a triage note the team can act on without asking anyone: whether it reproduces and where, the steps, expected versus actual, how often, a severity by this team's rubric with the reason, duplicates or related issues, the story and AC it breaks, and the change it likely came from. Missing information is asked for once, precisely. Nothing about the issue changes except one approved comment.

## Your Approach

Set your room status to `reading`. Read the report (Jira issue, Slack thread, or client message from the inbox item), its attachments and comments, then search Jira for duplicates by symptom, screen, and error text.

**Reproduce** where BOND allows: staging or a preview, with test accounts, never production. Record the environment, build, device, and each step. If you can't reproduce, say what you tried. If the report lacks what you need (version, account, steps), list exactly what is missing.

**Place it.** Find the story and AC the behavior breaks, and add or update a `regression` scenario for it in that story's scenario file with `status: fail` and the evidence. Look at recent PRs touching that area for the likely cause; name the change, never the person.

**Rate it** with BOND's severity rubric (the default lives there until First Breath sets one), with a one-line reason. A defect that BOND's release gates call blocking is noted as such for release-readiness.

**Write and raise.** Write `outputs/qa/<YYYY-MM-DD>-triage-<key>.md`. Raise one aor-signal `approval --target jira --action comment --target-url <issue link>` with the triage note: the facts, the suggested severity and why, duplicates, the likely change, and what's missing. Never set the severity, priority, status, or assignee yourself. A defect that is a client escalation or takes production down is a fire (`client_escalation` or `other`, with the issue as ref).

**Log and hand back.** Log `[qa] triaged <key>: <reproduced or not>, <severity>` with the note path. Set your status to `idle`, and end with the hand-back block.
