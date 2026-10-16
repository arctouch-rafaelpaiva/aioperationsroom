#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Unit tests for wake.py and init-sanctum.py (per-project squad memory). Run: uv run scripts/tests/test_wake.py"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
PROJECTS = "_bmad/memory/aor/projects"

ROSTER = """roster:
- id: aor-agent-pm
  role: pm
  skill: aor-agent-pm
- id: aor-agent-qa
  role: qa
  skill: aor-agent-qa
{extra}"""


def make_project(root: Path, pid: str, extra: str = "") -> None:
    base = root / PROJECTS / pid
    base.mkdir(parents=True)
    (base / "project.yaml").write_text(f"schema: 1\nid: {pid}\nname: {pid.title()}\nstatus: active\n" + ROSTER.format(extra=extra))
    (base / "index.md").write_text(f"# {pid}\n")


class SquadWakeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_project(self.root, "payments", "  name: Rui\n- id: aor-custom-mobile-mo\n  role: custom\n  skill: aor-agent-qa\n  name: Mo\n  persona: Paranoid about currency edge cases\n")
        make_project(self.root, "atlas")

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, name, *argv):
        res = subprocess.run([sys.executable, "-B", str(SCRIPTS / name), str(self.root), *argv], capture_output=True, text=True)
        return res.returncode, res.stdout

    def wake(self, *argv):
        code, out = self.run_script("wake.py", *argv)
        self.assertEqual(code, 0, out)
        return out

    def squad(self, pid, member="aor-agent-qa"):
        return self.root / PROJECTS / pid / "squad" / member

    def test_chat_without_project_lists_this_skills_projects(self):
        out = self.wake()
        self.assertIn("MODE: NEED_PROJECT", out)
        self.assertIn("atlas, payments", out)

    def test_chat_without_sanctum_is_first_breath_and_writes_nothing(self):
        self.assertIn("MODE: FIRST_BREATH", self.wake("--project", "atlas"))
        self.assertFalse(self.squad("atlas").exists())

    def test_headless_seeds_per_project_memory_with_roster_name(self):
        out = self.wake("--project", "payments", "--headless", "--task", "TS")
        self.assertIn("AUTO-INIT", out)
        self.assertIn("MODE: HEADLESS", out)
        self.assertIn("CALIBRATION: pending", out)
        self.assertIn("TASK: TS", out)
        for code in ("[TS]", "[CC]", "[DT]", "[RE]", "[PA]", "[CU]"):
            self.assertIn(code, out)
        persona = (self.squad("payments") / "PERSONA.md").read_text()
        self.assertIn("**Name:** Rui", persona)
        self.assertIn("**Project:** payments", persona)
        creed = (self.squad("payments") / "CREED.md").read_text()
        self.assertNotIn(str(self.root), creed)
        self.assertIn("{project-root}/_bmad/memory/aor/projects/payments/squad/aor-agent-qa", creed)
        self.assertFalse(self.squad("atlas").exists())
        self.wake("--project", "atlas", "--headless")
        self.assertIn("**Name:** Vera", (self.squad("atlas") / "PERSONA.md").read_text())
        self.assertIn("SEEDED SANCTUM", self.wake("--project", "payments"))

    def test_custom_member_gets_its_own_memory_and_persona(self):
        self.wake("--project", "payments", "--member", "aor-custom-mobile-mo", "--headless")
        persona = (self.squad("payments", "aor-custom-mobile-mo") / "PERSONA.md").read_text()
        self.assertIn("**Name:** Mo", persona)
        self.assertIn("Paranoid about currency edge cases", persona)
        self.assertFalse(self.squad("payments").exists())

    def test_unknown_project_or_member_is_reported(self):
        self.assertIn("PROJECT OR MEMBER NOT FOUND", self.wake("--project", "ghost", "--headless"))
        self.assertIn("not on atlas's roster", self.wake("--project", "atlas", "--member", "aor-custom-x", "--headless"))

    def test_born_member_wakes_and_init_is_idempotent(self):
        self.wake("--project", "atlas", "--headless")
        creed = self.squad("atlas") / "CREED.md"
        text = creed.read_text()
        start = text.index("{Discovered during First Breath.")
        creed.write_text(text[:start] + "Atlas ships on evidence." + text[text.index("}", start) + 1:])
        self.assertIn("MODE: WAKING", self.wake("--project", "atlas"))
        self.assertIn("CALIBRATION: done", self.wake("--project", "atlas", "--headless"))
        code, out = subprocess.run([sys.executable, "-B", str(SCRIPTS / "init-sanctum.py"), str(self.root), str(SCRIPTS.parent),
                                    "--project", "atlas"], capture_output=True, text=True).returncode, None
        self.assertEqual(code, 0)
        self.assertIn("Atlas ships on evidence.", creed.read_text())

    def test_init_rejects_member_running_another_skill(self):
        res = subprocess.run([sys.executable, "-B", str(SCRIPTS / "init-sanctum.py"), str(self.root), str(SCRIPTS.parent),
                              "--project", "payments", "--member", "aor-agent-pm"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 1)
        self.assertIn("runs aor-agent-pm", json.loads(res.stdout)["error"])


if __name__ == "__main__":
    unittest.main()
