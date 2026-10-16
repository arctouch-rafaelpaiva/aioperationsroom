# Scenario File Format

One file per story in `outputs/qa/`, named `<YYYY-MM-DD>-scenarios-<story key>.md`, so `scripts/qa_matrix.py` can trace every AC to scenarios and results. Write the steps in the team's test format and language (BOND); the field names stay in English, because the script reads them. Update the same file as results come in, and never start a second file for the same story.

```markdown
---
project: payments
story: PAY-142
ac: 3              # how many acceptance criteria the story has
item: in-…         # the inbox item this answers
---

# PAY-142 Customer requests a full refund

## Scenario: Full refund within 30 days
covers: AC1, AC2
kind: happy
test: tests/refund.spec.ts > full refund     # automated test id, manual, or none
status: pass                                  # untested | pass | fail | blocked
evidence: https://github.com/acme/pay/actions/runs/123
Given a paid order from 10 days ago
When the customer requests a full refund and confirms
Then the order shows "Refund requested" and the amount matches the charge

## Scenario: Refund after 30 days is refused
covers: AC1
kind: boundary
test: none
status: untested
Given a paid order from exactly 31 days ago
When the customer opens the order
Then no refund option is shown, and the policy link is

## Challenge
- AC2 says "handles errors" without saying which; scenarios for provider timeout are blocked — owner: requirements
```

**Kinds:** happy, negative, boundary, state, permission, data, a11y, regression.

**What the script enforces.** A story key and the AC count; at least one scenario; every AC covered; covers only within the AC count; known kinds and statuses; `evidence:` on every pass or fail. It warns when an AC has only happy-path scenarios or a scenario has no `test:` line. An AC's result is its worst scenario: fail, then blocked, then untested, then pass.
