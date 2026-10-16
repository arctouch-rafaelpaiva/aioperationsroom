#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Unit tests for wake.py (mode routing, auto-init, curator, portfolio). Run: uv run scripts/tests/test_wake.py"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
SANCTUM = "_bmad/memory/aor-agent-maestro"


def make_project(root: Path, pid: str) -> None:
    base = root / "_bmad/memory/aor/projects" / pid
    base.mkdir(parents=True)
    (base / "project.yaml").write_text(f"schema: 1\nid: {pid}\nname: {pid.title()}\nstatus: active\n")


class WakeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_project(self.root, "payments")

    def tearDown(self):
        self.tmp.cleanup()

    def wake(self, *argv):
        res = subprocess.run([sys.executable, "-B", str(SCRIPTS / "wake.py"), str(self.root), *argv], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        return res.stdout

    def test_chat_without_sanctum_is_first_breath(self):
        self.assertIn("MODE: FIRST_BREATH", self.wake())
        self.assertFalse((self.root / SANCTUM).exists())

    def test_pulse_seeds_sanctum_with_fixed_name_and_pending_calibration(self):
        out = self.wake("--pulse", "--task", "relay")
        self.assertIn("AUTO-INIT", out)
        self.assertIn("MODE: PULSE", out)
        self.assertIn("CALIBRATION: pending", out)
        self.assertIn("SANCTUM CURATOR: no", out)
        self.assertIn("===== PULSE.md =====", out)
        self.assertIn("===== PORTFOLIO", out)
        self.assertIn("MISSING STAND-UPS: payments", out)
        sanctum = self.root / SANCTUM
        self.assertIn("**Name:** Maestro", (sanctum / "PERSONA.md").read_text())
        caps = (sanctum / "CAPABILITIES.md").read_text()
        for code in ("[MB]", "[RL]", "[CI]"):
            self.assertIn(code, caps)
        for script in ("slack_post.py", "slack_replies.py", "portfolio.py"):
            self.assertTrue((sanctum / "scripts" / script).is_file(), script)
        self.assertFalse((sanctum / "references/first-breath.md").exists())
        self.assertIn("SEEDED SANCTUM", self.wake())

    def test_born_agent_wakes_and_only_brief_curates(self):
        self.wake("--pulse")
        creed = self.root / SANCTUM / "CREED.md"
        text = creed.read_text()
        start = text.index("{Discovered during First Breath.")
        creed.write_text(text[:start] + "Keep Ana's mornings clear." + text[text.index("}", start) + 1:])
        self.assertIn("MODE: WAKING", self.wake())
        self.assertIn("CALIBRATION: done", self.wake("--pulse", "--task", "relay"))
        self.assertIn("SANCTUM CURATOR: yes", self.wake("--pulse", "--task", "brief"))


if __name__ == "__main__":
    unittest.main()
