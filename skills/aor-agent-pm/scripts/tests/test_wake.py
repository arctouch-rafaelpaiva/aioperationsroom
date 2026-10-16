#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Unit tests for wake.py and init-sanctum.py (one PM per squad). Run: uv run scripts/tests/test_wake.py"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
PROJECTS = "_bmad/memory/aor/projects"


def make_project(root: Path, pid: str, status: str = "active", pm_name: str = "") -> Path:
    base = root / PROJECTS / pid
    base.mkdir(parents=True)
    name = f"  name: {pm_name}\n" if pm_name else ""
    (base / "project.yaml").write_text(f"schema: 1\nid: {pid}\nname: {pid.title()}\nstatus: {status}\n"
                                       f"roster:\n- id: aor-agent-pm\n  role: pm\n  skill: aor-agent-pm\n{name}")
    (base / "index.md").write_text(f"# {pid}\n")
    return base


class WakeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_project(self.root, "alpha")
        make_project(self.root, "payments", pm_name="Rita")
        make_project(self.root, "old", status="archived")

    def tearDown(self):
        self.tmp.cleanup()

    def wake(self, *argv):
        res = subprocess.run([sys.executable, "-B", str(SCRIPTS / "wake.py"), str(self.root), *argv], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        return res.stdout

    def sanctum(self, pid):
        return self.root / PROJECTS / pid / "squad" / "aor-agent-pm"

    def test_chat_without_project_lists_active_projects(self):
        out = self.wake()
        self.assertIn("MODE: NEED_PROJECT", out)
        self.assertIn("alpha, payments", out)

    def test_chat_without_sanctum_is_first_breath(self):
        self.assertIn("MODE: FIRST_BREATH", self.wake("--project", "payments"))
        self.assertFalse(self.sanctum("payments").exists())

    def test_pulse_seeds_this_projects_pm_only(self):
        out = self.wake("--pulse", "--task", "standup", "--project", "payments")
        self.assertIn("AUTO-INIT", out)
        self.assertIn("MODE: PULSE", out)
        self.assertIn("CALIBRATION: pending", out)
        self.assertIn("SANCTUM CURATOR: no", out)
        self.assertIn("===== PULSE.md =====", out)
        self.assertIn("===== PROJECT payments", out)
        for code in ("[SU]", "[TR]", "[EW]", "[WU]", "[PA]"):
            self.assertIn(code, out)
        self.assertIn("**Name:** Rita", (self.sanctum("payments") / "PERSONA.md").read_text())
        self.assertTrue((self.sanctum("payments") / "PULSE.md").is_file())
        self.assertFalse(self.sanctum("alpha").exists())
        self.assertFalse((self.root / "_bmad/memory/aor-agent-pm").exists())
        self.wake("--pulse", "--project", "alpha")
        self.assertIn("**Name:** Stella", (self.sanctum("alpha") / "PERSONA.md").read_text())
        self.assertIn("SEEDED SANCTUM", self.wake("--project", "payments"))

    def test_born_pm_wakes_and_every_wrap_curates_its_own_project(self):
        self.wake("--pulse", "--project", "payments")
        creed = self.sanctum("payments") / "CREED.md"
        text = creed.read_text()
        start = text.index("{Discovered during First Breath.")
        creed.write_text(text[:start] + "Payments ships on cue." + text[text.index("}", start) + 1:])
        self.assertIn("MODE: WAKING", self.wake("--project", "payments"))
        self.assertIn("CALIBRATION: done", self.wake("--pulse", "--task", "triage", "--project", "payments"))
        self.assertIn("SANCTUM CURATOR: yes", self.wake("--pulse", "--task", "eod", "--project", "payments"))
        self.assertIn("SANCTUM CURATOR: yes", self.wake("--pulse", "--task", "eod", "--project", "alpha"))

    def test_unknown_project_is_reported(self):
        self.assertIn("PROJECT NOT FOUND", self.wake("--pulse", "--task", "triage", "--project", "ghost"))


if __name__ == "__main__":
    unittest.main()
