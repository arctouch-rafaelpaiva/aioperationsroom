#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Unit tests for stories.py (draft checks and the Jira payload). Run: uv run scripts/tests/test_stories.py"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stories  # noqa: E402

GOOD = """---
project: payments
jira_project: PAY
labels: refunds, aor
---

# Epic: Refund flow
Customers want to refund without support (discovery brief).

## Story: Customer requests a full refund
As a customer, I want to request a full refund from my order page, so that I don't have to contact support.

### Acceptance criteria
1. Given a paid order under 30 days old, when the customer taps "Request refund", then the full amount is shown before they confirm.
2. Given the customer confirms,
   when the refund is accepted, then the order shows "Refund requested".

### Business rules
- Refunds go back to the original payment method.

### Dependencies
- PAY-118 provider refund API

## Story: Support sees refund requests
As a support agent, I want to see refund requests in the queue, so that I can follow up on failures.

### Acceptance criteria
1. Given a refund request, when support opens the queue, then it is listed with its status.

### Open questions
- Should failed refunds page on-call? — owner: engineering
"""


class StoriesTest(unittest.TestCase):
    def test_good_draft_passes_and_reports_readiness(self):
        result = stories.check(stories.parse(GOOD))
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual((result["ready"], result["not_ready"]), (1, 1))
        self.assertEqual(result["stories"][0]["dependencies"], ["PAY-118"])
        self.assertEqual(result["stories"][0]["ac"], 2)

    def test_errors_for_missing_structure_and_bad_ac(self):
        bad = """---
jira_project: pay
---
## Story: Thing
Make it work.

### Acceptance criteria
- It works as expected
"""
        result = stories.check(stories.parse(bad))
        errors = " | ".join(result["errors"])
        for fragment in ("jira_project", "# Epic:", "user-story line", "not Given/When/Then"):
            self.assertIn(fragment, errors)
        self.assertTrue(any("vague (works as expected)" in w for w in result["warnings"]))

    def test_checklist_format_and_existing_epic(self):
        draft = GOOD.replace("labels: refunds, aor", "epic: PAY-140\nac_format: checklist").replace(
            "1. Given a refund request, when support opens the queue, then it is listed with its status.", "- Listed with status")
        result = stories.check(stories.parse(draft))
        self.assertTrue(result["ok"], result["errors"])
        body = stories.payload(stories.parse(draft))
        self.assertEqual(body["epic"], {"key": "PAY-140"})

    def test_payload_is_one_batch_with_full_descriptions(self):
        body = stories.payload(stories.parse(GOOD))
        self.assertEqual((body["target"], body["action"], body["project_key"]), ("jira", "create_issues", "PAY"))
        self.assertEqual(body["epic"]["summary"], "Refund flow")
        self.assertEqual([i["summary"] for i in body["issues"]], ["Customer requests a full refund", "Support sees refund requests"])
        desc = body["issues"][0]["description"]
        self.assertIn("**Acceptance criteria**\n1. Given a paid order", desc)
        self.assertIn("2. Given the customer confirms, when the refund", desc)
        self.assertIn("**Business rules**\n- Refunds go back", desc)
        self.assertEqual(body["issues"][0]["labels"], ["refunds", "aor"])

    def test_cli_payload_refuses_draft_with_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad, good, out = Path(tmp, "bad.md"), Path(tmp, "good.md"), Path(tmp, "p.json")
            bad.write_text(GOOD.replace("jira_project: PAY\n", ""))
            good.write_text(GOOD)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(stories.main(["payload", "--file", str(bad), "--out", str(out)]), 1)
            self.assertFalse(out.exists())
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(stories.main(["payload", "--file", str(good), "--out", str(out)]), 0)
            self.assertEqual(json.loads(buf.getvalue())["preview"], "Create epic + 2 stories in PAY")
            self.assertEqual(json.loads(out.read_text())["project_key"], "PAY")

    def test_too_many_ac_warns_to_split(self):
        many = GOOD.replace("labels: refunds, aor", "max_ac: 1")
        self.assertTrue(any("consider splitting" in w for w in stories.check(stories.parse(many))["warnings"]))


if __name__ == "__main__":
    unittest.main()
