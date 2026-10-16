#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Unit tests for qa_matrix.py (AC tracing and release verdicts). Run: uv run scripts/tests/test_qa_matrix.py"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qa_matrix  # noqa: E402

FILE = """---
story: PAY-142
ac: 2
---

## Scenario: Full refund
covers: AC1, AC2
kind: happy
test: tests/refund.spec.ts > full refund
status: pass
evidence: https://ci/runs/1
Given a paid order
When the customer refunds
Then the order shows refund requested

## Scenario: Refund after 30 days
covers: AC1
kind: boundary
test: none
status: {boundary}

## Challenge
- AC2 is vague — owner: requirements
"""


def doc(boundary="pass\nevidence: https://ci/runs/2"):
    return qa_matrix.parse(FILE.format(boundary=boundary))


class QaMatrixTest(unittest.TestCase):
    def test_check_builds_matrix_with_worst_result_and_warnings(self):
        c = qa_matrix.check(doc("untested"))
        self.assertTrue(c["ok"], c["errors"])
        self.assertEqual(c["matrix"]["AC1"]["result"], "untested")
        self.assertEqual(c["matrix"]["AC2"]["result"], "pass")
        self.assertTrue(any("AC2 only has happy-path" in w for w in c["warnings"]))
        self.assertEqual(c["challenges"], ["AC2 is vague — owner: requirements"])
        self.assertEqual(c["matrix"]["AC1"]["scenarios"], ["Full refund", "Refund after 30 days"])

    def test_check_errors(self):
        text = "---\nstory: PAY-1\nac: 3\n---\n## Scenario: A\ncovers: AC1, AC4\nkind: smoke\nstatus: pass\n"
        c = qa_matrix.check(qa_matrix.parse(text))
        errors = " | ".join(c["errors"])
        for fragment in ("kind 'smoke'", "needs evidence", "covers AC4", "AC2 has no scenario", "AC3 has no scenario"):
            self.assertIn(fragment, errors)

    def test_verdict_rules(self):
        green = qa_matrix.check(doc())
        self.assertEqual(qa_matrix.verdict([green], [], {"critical", "high"})["verdict"], "go")
        low = [{"key": "PAY-9", "severity": "low", "open": True, "summary": "typo"}]
        v = qa_matrix.verdict([green], low, {"critical", "high"})
        self.assertEqual((v["verdict"], v["notes"]), ("go", ["PAY-9 (low) open: typo"]))
        medium = [{"key": "PAY-8", "severity": "medium", "open": True}, {"key": "PAY-7", "severity": "high", "open": False}]
        self.assertEqual(qa_matrix.verdict([green], medium, {"critical", "high"})["verdict"], "go-with-risks")
        self.assertEqual(qa_matrix.verdict([qa_matrix.check(doc("blocked"))], [], {"critical", "high"})["verdict"], "go-with-risks")
        failed = qa_matrix.verdict([qa_matrix.check(doc("fail\nevidence: https://ci/runs/3"))], [], {"critical", "high"})
        self.assertEqual(failed["verdict"], "no-go")
        self.assertIn("PAY-142 AC1 failed", failed["no_go"])
        high = qa_matrix.verdict([green], [{"key": "PAY-6", "severity": "High", "open": True}], {"critical", "high"})
        self.assertEqual(high["verdict"], "no-go")

    def test_uncovered_ac_blocks_release_once(self):
        c = qa_matrix.check(qa_matrix.parse(FILE.format(boundary="pass\nevidence: x").replace("ac: 2", "ac: 3")))
        v = qa_matrix.verdict([c], [], {"critical"})
        self.assertEqual(v["verdict"], "no-go")
        self.assertEqual(v["no_go"], ["PAY-142 AC3 has no scenario"])

    def test_cli_check_exit_codes_and_markdown_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp, "good.md"), Path(tmp, "bad.md")
            good.write_text(FILE.format(boundary="pass\nevidence: https://ci/runs/2"))
            bad.write_text("---\nstory: X\n---\n")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(qa_matrix.main(["check", "--file", str(good)]), 0)
                self.assertEqual(qa_matrix.main(["check", "--file", str(bad)]), 1)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(qa_matrix.main(["verdict", "--file", str(good), "--format", "md"]), 0)
            self.assertIn("**Verdict: go**", buf.getvalue())
            self.assertIn("| PAY-142 | 2 | 2 | 0 | 0 | 0 | 0 |", buf.getvalue())
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(qa_matrix.main(["verdict", "--file", str(good), "--defects", str(Path(tmp, "missing.json"))]), 2)
            self.assertFalse(json.loads(buf.getvalue())["ok"])


if __name__ == "__main__":
    unittest.main()
