#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Unit tests for evidence.py. Run: uv run scripts/tests/test_evidence.py"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import evidence  # noqa: E402


def ev(i, who, source, themes, day="2026-10-10"):
    return {"id": f"ev-{i}", "date": day, "source": source, "ref": f"https://x/{i}", "who": who,
            "segment": "smb", "quote": "Refunds take forever", "themes": themes}


LEDGER = {
    "goals": {"G2": "Cut support load"},
    "themes": {"refund-delay": {"name": "Refunds take too long", "goal": "G2"}, "csv-export": {"name": "CSV export"}},
    "evidence": [
        ev(1, "Customer A (SMB)", "support", ["refund-delay"]),
        ev(2, "Customer B (SMB)", "support", ["refund-delay"]),
        ev(3, "Customer C (Enterprise)", "interview", ["refund-delay"], "2026-10-14"),
        ev(4, "Customer A (SMB)", "jira", ["refund-delay"]),
        ev(5, "Ana (client sponsor)", "stakeholder", ["csv-export"], "2026-09-01"),
        ev(6, "Customer D", "slack", []),
    ],
}


class EvidenceTest(unittest.TestCase):
    def test_valid_ledger(self):
        out = evidence.check(LEDGER)
        self.assertTrue(out["ok"], out["errors"])
        self.assertEqual(out["warnings"], ["theme csv-export has no goal"])

    def test_check_errors_including_personal_data(self):
        bad = yaml.safe_load(yaml.safe_dump(LEDGER))
        bad["themes"]["x"] = {"name": "X", "goal": "G9"}
        bad["evidence"] += [
            {"id": "ev-1", "date": "10/12/2026", "source": "email", "ref": "r", "who": "joe@acme.com", "quote": "call me at +55 11 99999-1234", "themes": ["nope"]},
            {"id": "ev-8", "source": "jira"},
        ]
        errors = " | ".join(evidence.check(bad)["errors"])
        for fragment in ("goal G9", "id is used twice", "date must be", "source 'email'", "who contains an email",
                         "quote contains an email or phone", "theme nope", "evidence ev-8 needs quote"):
            self.assertIn(fragment, errors)

    def test_rank_strength_and_order(self):
        out = evidence.rank(LEDGER)
        first, second = out["themes"]
        self.assertEqual((first["theme"], first["people"], first["channels"], first["mentions"], first["strength"]),
                         ("refund-delay", 3, ["interview", "jira", "support"], 4, "strong"))
        self.assertEqual((first["first_seen"], first["last_seen"], first["goal"]), ("2026-10-10", "2026-10-14", "G2"))
        self.assertEqual((second["theme"], second["strength"]), ("csv-export", "anecdote"))
        self.assertEqual(out["untagged"], 1)
        recent = evidence.rank(LEDGER, date(2026, 10, 1))
        self.assertEqual([t["theme"] for t in recent["themes"]], ["refund-delay"])

    def test_dates_and_amounts_in_quotes_are_not_phone_numbers(self):
        ok = yaml.safe_load(yaml.safe_dump(LEDGER))
        ok["evidence"][0]["quote"] = "Since 2026-10-12 we lost R$ 1.000,00 on order 12345"
        self.assertTrue(evidence.check(ok)["ok"], evidence.check(ok)["errors"])

    def test_emerging(self):
        self.assertEqual(evidence.strength(2, 1), "emerging")
        self.assertEqual(evidence.strength(3, 1), "emerging")

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp, "evidence.yaml")
            f.write_text(yaml.safe_dump(LEDGER))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(evidence.main(["themes", "--file", str(f), "--since", "2026-10-01"]), 0)
            self.assertEqual(json.loads(buf.getvalue())["themes"][0]["strength"], "strong")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(evidence.main(["check", "--file", str(Path(tmp, "missing.yaml"))]), 2)


if __name__ == "__main__":
    unittest.main()
