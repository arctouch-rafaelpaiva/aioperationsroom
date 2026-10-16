#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Unit tests for glossary.py. Run: uv run scripts/tests/test_glossary.py"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import glossary  # noqa: E402

TERMS = [
    {"term": "Cancel order", "definition": "Stops an unpaid order.", "avoid": ["Void", "Cancel purchase"]},
    {"term": "Refund", "definition": "Returns money for a paid order.", "avoid": ["Chargeback"]},
]
DOC = """# Refunds PRD
Customers can Void an order before payment. Use cancel purchase sparingly.
The Refund Limit applies. The Refund Limit is R$1,000. Another Refund Limit note.
The voided state is different.
```
void(order)  # code is skipped
```
SLA is 2 days. The SLA matters. Check the SLA.
"""


class GlossaryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.doc = Path(self.tmp.name, "prd.md")
        self.doc.write_text(DOC)

    def tearDown(self):
        self.tmp.cleanup()

    def test_check_finds_glossary_problems(self):
        self.assertTrue(glossary.check(TERMS)["ok"])
        bad = TERMS + [{"term": "Void", "definition": ""}, {"term": "refund", "definition": "x", "avoid": ["Void"]}]
        errors = " | ".join(glossary.check(bad)["errors"])
        for fragment in ("'refund' is defined twice", "'Void' has no definition", "avoided under both", "'Void' is a term"):
            self.assertIn(fragment, errors)

    def test_scan_whole_words_outside_code(self):
        out = glossary.scan(TERMS, [str(self.doc)])
        self.assertEqual([(h["line"], h["found"], h["use"]) for h in out["hits"]],
                         [(2, "Void", "Cancel order"), (2, "cancel purchase", "Cancel order")])
        self.assertEqual(out["summary"], {"Cancel order": 2})

    def test_candidates_skip_known_terms(self):
        out = glossary.candidates(TERMS, [str(self.doc)], 3)
        self.assertEqual([(c["phrase"], c["count"]) for c in out["candidates"]], [("Refund Limit", 3), ("SLA", 3)])

    def test_cli_exit_codes(self):
        bad = Path(self.tmp.name, "g.yaml")
        bad.write_text("terms:\n  - term: X\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(glossary.main(["check", "--glossary", str(bad)]), 1)
            self.assertEqual(glossary.main(["scan", "--glossary", str(bad)]), 2)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(glossary.main(["scan", "--glossary", str(bad), "--file", str(self.doc)]), 0)
        self.assertEqual(json.loads(buf.getvalue())["hits"], [])


if __name__ == "__main__":
    unittest.main()
