#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Unit tests for room_setup.py. Run: uv run scripts/tests/test_room_setup.py"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import room_setup  # noqa: E402


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = room_setup.main(argv)
    return code, json.loads(buf.getvalue())


class RoomSetupTest(unittest.TestCase):
    def test_scaffold_gitignore_and_checklist_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "_bmad").mkdir()
            (root / "_bmad" / "config.yaml").write_text(
                "aor:\n  aor_timezone: America/Sao_Paulo\n  aor_brief_time: '08:30'\n  aor_slack_batch_minutes: 15\n  aor_ops_repo: acme-ops\n")
            (root / ".gitignore").write_text("node_modules\n")
            code, out = run(["--root", str(root)])
            self.assertEqual(code, 0)
            self.assertEqual(out["created"], ["_bmad/memory/aor/projects", "aor/room"])
            self.assertEqual(out["gitignore"], "added")
            self.assertEqual(out["warnings"], ["no git remote: push the ops repo to a private remote so automations can clone it"])
            self.assertEqual((root / ".gitignore").read_text(), "node_modules\n_bmad/config.user.yaml\n")
            text = (root / "_bmad/memory/aor/automations.md").read_text()
            self.assertIn("`acme-ops` repo", text)
            self.assertIn("Mon–Fri 08:30 America/Sao_Paulo (UTC cron `30 11 * * 1-5`)", text)
            self.assertIn("Every 15 minutes, every day (cron `*/15 * * * *`)", text)
            self.assertIn("aor-agent-maestro --pulse --task relay", text)
            code, again = run(["--root", str(root)])
            self.assertEqual((again["created"], again["gitignore"]), ([], "already ignored"))
            self.assertEqual((root / ".gitignore").read_text().count("config.user.yaml"), 1)

    def test_dry_run_writes_nothing_and_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run(["--root", tmp, "--dry-run"])
            self.assertEqual(code, 0)
            self.assertEqual(list(Path(tmp).iterdir()), [])
            self.assertTrue(any("not a git repo" in w for w in out["warnings"]))
            self.assertTrue(any("config.yaml not found" in w for w in out["warnings"]))

    def test_cron_edge_cases(self):
        now = datetime(2026, 10, 16, tzinfo=timezone.utc)
        self.assertIsNone(room_setup.utc_cron_weekdays("23:30", "America/Sao_Paulo", now))
        self.assertIsNone(room_setup.utc_cron_weekdays("8:30", "UTC", now))
        text = room_setup.checklist({**room_setup.DEFAULTS, "aor_slack_batch_minutes": "45"}, now)
        self.assertIn("Every 45 minutes, every day |", text)

    def test_missing_root(self):
        self.assertEqual(run(["--root", "/nonexistent/aor"])[0], 2)


if __name__ == "__main__":
    unittest.main()
