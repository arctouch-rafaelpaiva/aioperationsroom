#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Unit tests for project_registry.py. Run: uv run scripts/tests/test_project_registry.py"""

from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import project_registry  # noqa: E402

SOURCES = {
    "notion": [{"url": "https://www.notion.so/acme/PRD-hub-abc123", "kind": "page", "title": "PRD hub", "verified": "2026-10-16"}],
    "jira": {"site": "acme.atlassian.net", "projects": ["PAY"], "boards": [42], "verified": "2026-10-16"},
    "figma": [{"url": "https://www.figma.com/design/XYZ/Payments", "kind": "file", "verified": False}],
    "github": [{"repo": "acme/payments-app", "verified": "2026-10-16"}],
    "slack": [{"channel": "C0PAYTEAM1", "name": "#pay-team", "use": ["context", "post"], "verified": "2026-10-16"}],
}
NOW = "2026-10-16T12:00:00Z"


class ProjectRegistryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, *argv, expect=0):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            code = project_registry.main(["--root", str(self.root), "--now", NOW, *argv])
        self.assertEqual(code, expect, buf.getvalue())
        return json.loads(buf.getvalue())

    def spec(self, data: dict) -> str:
        path = self.root / f"spec-{len(list(self.root.glob('spec-*')))}.json"
        path.write_text(json.dumps(data))
        return str(path)

    def onboard(self, **extra):
        return self.run_cmd("onboard", "--spec", self.spec({"name": "Payments App", "sources": SOURCES, **extra}))

    def project_yaml(self, pid="payments-app") -> Path:
        return self.root / "_bmad/memory/aor/projects" / pid / "project.yaml"

    def test_onboard_writes_registry_scaffold_checklist_and_signals(self):
        out = self.onboard()
        self.assertEqual(out["project"], "payments-app")
        base = "_bmad/memory/aor/projects/payments-app/"
        for f in ["project.yaml", "index.md", "risks.md", "daily/.gitkeep", "inbox/.gitkeep", "standup/.gitkeep", "outputs/qa/.gitkeep", "automations.md"]:
            self.assertIn(base + f, out["changed"])
        self.assertEqual(len(out["room_signals"]), 7)
        self.assertEqual(out["room_signals"][0][:6], ["status", "--project", "payments-app", "--agent", "aor-agent-pm", "--status"])
        self.assertTrue(any("figma" in w and "unverified" in w for w in out["warnings"]))
        self.assertIn("UTC cron `0 11 * * 1-5`", out["checklist"])
        self.assertIn("acme/payments-app", out["checklist"])
        self.assertIn("#pay-team", out["checklist"])
        self.assertIn("jira, figma, notion", out["checklist"])
        self.assertIn("aor-agent-pm --pulse --task standup --project payments-app", out["checklist"])

    def test_fire_override_is_readable_by_aor_signal(self):
        self.onboard(fire={"blocker_fire_hours": 4})
        text = self.project_yaml().read_text()
        self.assertRegex(text, re.compile(r"^\s*blocker_fire_hours\s*:\s*4\b", re.M))

    def test_onboard_twice_is_rejected(self):
        self.onboard()
        out = self.run_cmd("onboard", "--spec", self.spec({"name": "Payments App", "sources": SOURCES}), expect=1)
        self.assertIn("already exists", out["error"])

    def test_bad_sources_are_rejected_with_fixes(self):
        bad = {"slack": [{"channel": "#pay-team", "use": ["context"]}], "jira": {"site": "acme.atlassian.net"}}
        out = self.run_cmd("onboard", "--spec", self.spec({"name": "Bad", "sources": bad}), expect=1)
        self.assertIn("channel id", out["error"])
        self.assertIn("projects, boards, jql", out["error"])
        self.assertFalse(self.project_yaml("bad").exists())
        out = self.run_cmd("onboard", "--spec", self.spec({"name": "Empty", "sources": {}}), expect=1)
        self.assertIn("where to look", out["error"])

    def test_custom_agent_needs_a_base_specialist(self):
        roster = [{"role": "pm"}, {"role": "custom", "name": "Security reviewer"}]
        out = self.run_cmd("onboard", "--spec", self.spec({"name": "Xenon", "sources": SOURCES, "roster": roster}), expect=1)
        self.assertIn("based_on", out["error"])
        roster[1]["based_on"] = "aor-agent-engineering"
        out = self.run_cmd("onboard", "--spec", self.spec({"name": "Xenon", "sources": SOURCES, "roster": roster}))
        self.assertEqual(out["room_signals"][1][4], "aor-custom-security-reviewer")
        self.assertIn("_bmad/memory/aor/projects/xenon/outputs/security-reviewer/.gitkeep", out["changed"])

    def test_roster_needs_exactly_one_pm(self):
        out = self.run_cmd("onboard", "--spec", self.spec({"name": "X", "sources": SOURCES, "roster": [{"role": "qa"}]}), expect=1)
        self.assertIn("exactly one pm", out["error"])

    def test_update_sources_replaces_and_removes_types(self):
        self.onboard()
        new_github = [{"repo": "acme/payments-api", "verified": "2026-10-16"}]
        out = self.run_cmd("update-sources", "--project", "payments-app", "--spec", self.spec({"sources": {"github": new_github, "figma": None}}))
        self.assertEqual(out["updated"], ["figma", "github"])
        listed = self.run_cmd("list")["projects"][0]
        self.assertEqual(listed["sources"], ["github", "jira", "notion", "slack"])
        self.assertIn("acme/payments-api", out["checklist"])
        self.assertNotIn("acme/payments-app", out["checklist"])

    def test_add_agent_and_duplicate(self):
        self.onboard(roster=[{"role": "pm"}, {"role": "qa"}])
        out = self.run_cmd("add-agent", "--project", "payments-app", "--role", "design", "--name", "Dani")
        self.assertEqual(out["agent"]["id"], "aor-agent-design")
        self.assertIn("_bmad/memory/aor/projects/payments-app/outputs/design/.gitkeep", out["changed"])
        self.assertEqual(out["room_signals"], [["status", "--project", "payments-app", "--agent", "aor-agent-design", "--status", "idle", "--task", "Joined the room"]])
        dup = self.run_cmd("add-agent", "--project", "payments-app", "--role", "design", expect=1)
        self.assertIn("already on", dup["error"])

    def test_archive_and_restore_in_place(self):
        self.onboard()
        out = self.run_cmd("archive", "--project", "payments-app")
        self.assertEqual(out["status"], "archived")
        self.assertTrue(all(s[6] == "offline" for s in out["room_signals"]))
        self.assertIn("disable every automation", out["checklist"])
        self.assertTrue((self.project_yaml().parent / "decisions.md").exists())
        self.assertIn("already archived", self.run_cmd("archive", "--project", "payments-app", expect=1)["error"])
        back = self.run_cmd("archive", "--project", "payments-app", "--restore")
        self.assertEqual(back["status"], "active")
        self.assertNotIn("archived_at", self.project_yaml().read_text())

    def test_validate_hand_edits_and_scaffold_never_overwrites(self):
        self.onboard()
        inbox = self.project_yaml().parent / "decisions.md"
        inbox.write_text("# Decisions\n- real item\n")
        (self.project_yaml().parent / "risks.md").unlink()
        out = self.run_cmd("validate", "--project", "payments-app", "--scaffold")
        self.assertEqual(out["changed"], ["_bmad/memory/aor/projects/payments-app/risks.md"])
        self.assertIn("real item", inbox.read_text())

        self.project_yaml().write_text(self.project_yaml().read_text().replace("id: payments-app", "id: payments") + "colour: blue\n")
        bad = self.run_cmd("validate", "--all", expect=1)
        errors = bad["projects"]["payments-app"]["errors"]
        self.assertTrue(any("folder name" in e for e in errors))
        self.assertTrue(any("unknown key 'colour'" in e for e in errors))

    def test_unquoted_yaml_dates_round_trip(self):
        self.onboard()
        text = self.project_yaml().read_text().replace("verified: '2026-10-16'", "verified: 2026-10-16")
        self.project_yaml().write_text(text)
        self.assertTrue(self.run_cmd("validate", "--project", "payments-app")["ok"])

    def test_unknown_project_names_known_ones(self):
        self.onboard()
        out = self.run_cmd("archive", "--project", "nope", expect=1)
        self.assertIn("known: payments-app", out["error"])


if __name__ == "__main__":
    unittest.main()
