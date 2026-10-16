# Story Draft Format

Every story draft in `outputs/requirements/` uses this shape, so `scripts/stories.py` can check it and build the exact Jira payload the operator approves. Write the content in the team's language (BOND); the headings stay in English, because the script reads them.

```markdown
---
project: payments
jira_project: PAY          # the Jira project key
epic: PAY-140              # an existing epic; omit it to create the epic below
item: in-20261016-…        # the inbox item this answers
ac_format: gwt             # gwt (Given/When/Then) or checklist, per BOND
labels: refunds, aor       # optional, comma-separated
max_ac: 8                  # optional; more AC than this warns "consider splitting"
---

# Epic: Refund flow
Why this epic exists, the outcome, and the evidence (link discovery's brief).

## Story: Customer requests a full refund
As a customer, I want to request a full refund from my order page, so that I don't have to contact support.

### Acceptance criteria
1. Given a paid order under 30 days old, when the customer taps "Request refund", then the full amount and the refund method are shown before they confirm.
2. Given the customer confirms, when the refund is accepted, then the order shows "Refund requested" and an email is sent within 5 minutes.

### Business rules
- Refunds go back to the original payment method.

### Edge cases
- The order was paid partly with store credit.

### Dependencies
- PAY-118 payment-provider refund API

### Out of scope
- Partial refunds (separate story)

### Open questions
- Can a refund exceed the original charge when shipping was added later? — owner: finance
```

**Rules the script enforces.** A Jira project key; an existing epic key or a new epic with a description; at least one story; a user-story line (As a …, I want …, so that …) in every story; at least one AC per story, each in Given/When/Then when `ac_format` is `gwt`; no duplicate story titles. It warns about vague AC wording, unknown sections, and stories with more AC than `max_ac`. A story with open questions is reported as not ready. The draft can still go up for approval, but the hand-back and the approval rationale must say so.
