#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Unit tests for portfolio.py (stand-ups, silence, inbox, unsorted). Run: uv run scripts/tests/test_portfolio.py"""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import portfolio  # noqa: E402

NOW = datetime.fromisoformat("2026-10-16T11:40:00+00:00")  # 08:40 in São Paulo


class PortfolioTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.projects = self.root / "_bmad/memory/aor/projects"
        for pid, status in (("payments", "active"), ("atlas", "active"), ("old", "archived")):
            (self.projects / pid).mkdir(parents=True)
            (self.projects / pid / "project.yaml").write_text(f"schema: 1\nid: {pid}\nname: {pid.title()}\nstatus: {status}\n")
        pay = self.projects / "payments"
        (pay / "standup").mkdir()
        (pay / "standup/2026-10-16.md").write_text("Go: refunds QA (qa)\n")
        (pay / "daily/2026-10-16").mkdir(parents=True)
        (pay / "daily/2026-10-16/run-1.md").write_text("- 08:02 [pm] stand-up written\n- 07:55 [qa] started\n")
        (pay / "inbox").mkdir()
        (pay / "inbox/in-1.md").write_text("status: new\n")
        (pay / "inbox/in-2.md").write_text("status: routed\n")
        (pay / "inbox/in-3.md").write_text("status: done\n")
        (self.projects / "atlas/daily/2026-10-14").mkdir(parents=True)
        (self.projects / "atlas/daily/2026-10-14/run-0.md").write_text("- 11:00 [pm] wrap\n")
        sanctum = self.root / "_bmad/memory/aor-agent-maestro"
        (sanctum / "briefs").mkdir(parents=True)
        (sanctum / "briefs/2026-10-15.md").write_text("thread_ts: 1.0\n")
        for day, line in (("2026-10-14", "- old · stale"), ("2026-10-15", "- jane@acme.com · Invoice · link · candidates: none")):
            (sanctum / "unsorted" / day).mkdir(parents=True)
            (sanctum / "unsorted" / day / "r.md").write_text(line + "\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_portfolio_flags_missing_and_silent_and_counts_inbox(self):
        p = portfolio.portfolio(self.root, NOW, 26)
        self.assertEqual([x["id"] for x in p["projects"]], ["atlas", "payments"])
        self.assertEqual(p["missing_standups"], ["atlas"])
        self.assertEqual(p["silent_projects"], ["atlas"])
        pay = p["projects"][1]
        self.assertEqual((pay["inbox_open"], pay["inbox_untriaged"]), (2, 1))
        self.assertTrue(pay["last_activity"].startswith("2026-10-16T08:02"))
        self.assertEqual(p["unsorted"], ["- jane@acme.com · Invoice · link · candidates: none"])

    def test_render_leads_with_flags(self):
        md = portfolio.render(portfolio.portfolio(self.root, NOW, 26))
        lines = md.splitlines()
        self.assertEqual(lines[1], "MISSING STAND-UPS: atlas")
        self.assertIn("(no stand-up today)", md)
        self.assertIn("Go: refunds QA (qa)", md)


if __name__ == "__main__":
    unittest.main()
