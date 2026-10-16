#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Unit tests for room_signal.py. Run: uv run scripts/tests/test_room_signal.py"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import room_signal  # noqa: E402


class RoomSignalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ.pop("AOR_ROOM_URL", None)
        os.environ["AOR_RUN_ID"] = "test-run"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, *argv, now="2026-10-15T12:00:00Z", expect=0):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            code = room_signal.main(["--root", str(self.root), "--now", now, *argv])
        self.assertEqual(code, expect, buf.getvalue())
        return json.loads(buf.getvalue())

    def who(self, agent="aor-agent-pm", project="alpha"):
        return ["--project", project, "--agent", agent]

    def test_status_writes_per_run_file_and_folds(self):
        out = self.run_cmd("status", *self.who(), "--status", "reading", "--task", "Triage JIRA-12")
        self.assertEqual(out["file"], "aor/room/events/2026-10-15/test-run.jsonl")
        self.assertEqual(out["push"], "skipped")
        agents = self.run_cmd("state", "agents")["agents"]
        self.assertEqual(agents["alpha/aor-agent-pm"]["task"], "Triage JIRA-12")

    def test_ask_answer_flow_and_health(self):
        q = self.run_cmd("ask", *self.who(), "--question", "Ship Friday?", "--options", "yes|no")["item"]
        self.assertEqual(self.run_cmd("state", "projects")["projects"]["alpha"]["health"], "amber")
        self.run_cmd("resolve", "--item", q, "--decision", "answered", "--answer", "yes", "--by", "slack")
        item = self.run_cmd("state", "items", "--kind", "ask")["items"][0]
        self.assertEqual((item["status"], item["answer"]), ("answered", "yes"))
        self.assertEqual(self.run_cmd("state", "projects")["projects"]["alpha"]["health"], "green")

    def test_approval_lifecycle_and_guards(self):
        self.run_cmd("approval", *self.who("aor-agent-qa"), "--target", "jira", "--action", "comment",
                     "--preview", "x", "--rationale", "y", expect=1)
        ap = self.run_cmd("approval", *self.who("aor-agent-qa"), "--target", "jira", "--action", "comment",
                          "--preview", "Add test scenarios", "--rationale", "AC gaps", "--payload", "Scenario 1...")["item"]
        self.run_cmd("resolve", "--item", ap, "--decision", "done", "--by", "aor-agent-qa", expect=1)
        self.run_cmd("resolve", "--item", ap, "--decision", "edited", "--by", "room", expect=1)
        self.run_cmd("resolve", "--item", ap, "--decision", "edited", "--payload", "Scenario 1 (edited)", "--by", "room")
        ready = self.run_cmd("state", "items", "--owner", "aor-agent-qa", "--status", "edited")["items"]
        self.assertEqual(ready[0]["final_payload"], "Scenario 1 (edited)")
        self.run_cmd("resolve", "--item", ap, "--decision", "done", "--result-url", "https://jira/x", "--by", "aor-agent-qa")
        self.assertEqual(self.run_cmd("state", "items")["items"][0]["status"], "done")
        self.run_cmd("resolve", "--item", "nope", "--decision", "approved", "--by", "room", expect=1)

    def test_final_statuses_accept_no_further_resolves(self):
        q = self.run_cmd("ask", *self.who(), "--question", "Q")["item"]
        self.run_cmd("resolve", "--item", q, "--decision", "answered", "--answer", "a", "--by", "room")
        self.run_cmd("resolve", "--item", q, "--decision", "rejected", "--by", "room", expect=1)
        ap = self.run_cmd("approval", *self.who(), "--target", "github", "--action", "comment",
                          "--preview", "p", "--rationale", "r", "--payload", "body")["item"]
        self.run_cmd("resolve", "--item", ap, "--decision", "approved", "--by", "slack")
        self.run_cmd("resolve", "--item", ap, "--decision", "done", "--by", "aor-agent-pm")
        for decision in ("approved", "rejected", "done"):
            self.run_cmd("resolve", "--item", ap, "--decision", decision, "--by", "room", expect=1)

    def test_fold_ignores_illegal_hand_written_resolves(self):
        ap = self.run_cmd("approval", *self.who(), "--target", "jira", "--action", "comment",
                          "--preview", "p", "--rationale", "r", "--payload", "body")["item"]
        self.run_cmd("resolve", "--item", ap, "--decision", "approved", "--by", "slack")
        self.run_cmd("resolve", "--item", ap, "--decision", "done", "--by", "aor-agent-pm")
        bad = {"v": 1, "id": "ev-hand", "ts": "2026-10-15T12:00:01.000Z", "type": "resolve", "project": "alpha",
               "agent": "room", "run": "room-x", "data": {"item": ap, "decision": "approved", "by": "room"}}
        with (self.root / "aor/room/events/2026-10-15/room-x.jsonl").open("w") as fh:
            fh.write(json.dumps(bad) + "\n")
        self.assertEqual(self.run_cmd("state", "items", "--id", ap)["items"][0]["status"], "done")

    def test_operator_can_reject_or_reedit_until_posted(self):
        ap = self.run_cmd("approval", *self.who(), "--target", "notion", "--action", "update_page",
                          "--preview", "p", "--rationale", "r", "--payload", "v1")["item"]
        self.run_cmd("resolve", "--item", ap, "--decision", "approved", "--by", "slack")
        self.run_cmd("resolve", "--item", ap, "--decision", "edited", "--payload", "v2", "--by", "room")
        item = self.run_cmd("state", "items", "--id", ap)["items"][0]
        self.assertEqual((item["status"], item["final_payload"]), ("edited", "v2"))
        self.run_cmd("resolve", "--item", ap, "--decision", "rejected", "--by", "room")
        self.assertEqual(self.run_cmd("state", "items", "--id", ap)["items"][0]["status"], "rejected")

    def test_same_risk_id_in_two_projects_stays_separate(self):
        self.run_cmd("risk", "open", *self.who(project="alpha"), "--risk", "api-keys", "--title", "A")
        self.run_cmd("risk", "open", *self.who(project="beta"), "--risk", "api-keys", "--title", "B")
        risks = self.run_cmd("state", "risks")["risks"]
        self.assertEqual(sorted(risks), ["alpha|api-keys", "beta|api-keys"])
        self.run_cmd("risk", "close", *self.who(project="alpha"), "--risk", "api-keys")
        risks = self.run_cmd("state", "risks")["risks"]
        self.assertFalse(risks["alpha|api-keys"]["open"])
        self.assertTrue(risks["beta|api-keys"]["open"])
        fires = self.run_cmd("evaluate", now="2026-10-16T13:00:00Z")["new_fires"]
        self.assertEqual([(f["project"], f["ref"]) for f in fires], [("beta", "api-keys")])

    def test_fire_clear_that_matches_nothing_fails_loudly(self):
        self.run_cmd("fire", *self.who(), "--reason", "failed_build", "--detail", "red", "--ref", "ci/1")
        out = self.run_cmd("fire", *self.who(), "--reason", "failed_build", "--clear", expect=1)
        self.assertIn("ci/1", out["error"])
        self.assertEqual(self.run_cmd("state", "projects")["projects"]["alpha"]["health"], "red")

    def test_fire_is_deduped_and_clearable(self):
        first = self.run_cmd("fire", *self.who(), "--reason", "failed_build", "--detail", "main red", "--ref", "ci/1")
        again = self.run_cmd("fire", *self.who(), "--reason", "failed_build", "--detail", "still red", "--ref", "ci/1")
        self.assertTrue(first["alert"])
        self.assertFalse(again["alert"])
        self.assertEqual(self.run_cmd("state", "projects")["projects"]["alpha"]["health"], "red")
        self.run_cmd("fire", *self.who(), "--reason", "failed_build", "--ref", "ci/1", "--clear")
        self.assertEqual(self.run_cmd("state", "projects")["projects"]["alpha"]["health"], "green")

    def test_blocker_overdue_uses_default_and_project_override(self):
        rid = self.run_cmd("risk", "open", *self.who(), "--title", "Waiting on API keys", now="2026-10-14T10:00:00Z")["risk"]
        early = self.run_cmd("evaluate", now="2026-10-15T09:00:00Z")
        self.assertEqual(early["new_fires"], [])
        late = self.run_cmd("evaluate", now="2026-10-15T10:30:00Z")
        self.assertEqual(late["new_fires"][0]["reason"], "blocker_overdue")
        self.assertEqual(self.run_cmd("evaluate", now="2026-10-15T11:00:00Z")["new_fires"], [])
        self.run_cmd("risk", "close", *self.who(), "--risk", rid, now="2026-10-15T11:30:00Z")
        cleared = self.run_cmd("evaluate", now="2026-10-15T11:31:00Z")
        self.assertEqual(cleared["projects"]["alpha"]["health"], "green")

        proj = self.root / "_bmad/memory/aor/projects/beta"
        proj.mkdir(parents=True)
        (proj / "project.yaml").write_text("name: Beta\nfire:\n  blocker_fire_hours: 4\n")
        self.run_cmd("risk", "open", *self.who(project="beta"), "--title", "Design missing", now="2026-10-15T06:00:00Z")
        self.assertEqual(len(self.run_cmd("evaluate", now="2026-10-15T10:30:00Z")["new_fires"]), 1)

    def test_digest_batches_and_respects_quiet_hours(self):
        # 15:00Z = 12:00 BRT (outside quiet hours)
        self.run_cmd("ask", *self.who(), "--question", "Q1", now="2026-10-15T15:00:00Z")
        self.run_cmd("approval", *self.who("aor-agent-docs"), "--target", "notion", "--action", "update_page",
                     "--preview", "Fix glossary", "--rationale", "contradiction", "--payload", "text",
                     now="2026-10-15T15:01:00Z")
        d = self.run_cmd("digest", now="2026-10-15T15:05:00Z")
        self.assertTrue(d["send"])
        self.assertEqual(len(d["items"]), 2)
        ids = ",".join(i["id"] for i in d["items"])
        self.run_cmd("digest", "--mark-sent", ids, "--channel", "C0C9F0ERP35", "--thread-ts", "1.2", now="2026-10-15T15:05:00Z")
        self.assertEqual(self.run_cmd("digest", now="2026-10-15T15:06:00Z")["reason"], "nothing new")
        self.run_cmd("ask", *self.who(), "--question", "Q2", now="2026-10-15T15:10:00Z")
        held = self.run_cmd("digest", now="2026-10-15T15:20:00Z")
        self.assertEqual((held["send"], held["reason"]), (False, "batch window open"))
        self.assertTrue(self.run_cmd("digest", now="2026-10-15T15:36:00Z")["send"])
        # 23:00Z = 20:00 BRT (quiet hours)
        quiet = self.run_cmd("digest", now="2026-10-15T23:00:00Z")
        self.assertFalse(quiet["send"])
        self.assertIn("quiet hours", quiet["reason"])

    def test_push_failure_never_fails_the_command(self):
        os.environ["AOR_ROOM_URL"] = "http://127.0.0.1:9"
        try:
            out = self.run_cmd("status", *self.who(), "--status", "working", "--task", "x")
        finally:
            os.environ.pop("AOR_ROOM_URL", None)
        self.assertEqual(out["push"], "failed")
        self.assertTrue((self.root / out["file"]).is_file())

    def test_resolve_from_other_run_in_same_instant_still_applies(self):
        os.environ["AOR_RUN_ID"] = "zz-agent-run"
        q = self.run_cmd("ask", *self.who(), "--question", "Q")["item"]
        os.environ["AOR_RUN_ID"] = "aa-room"
        self.run_cmd("resolve", "--item", q, "--decision", "answered", "--answer", "ok", "--by", "room")
        self.assertEqual(self.run_cmd("state", "items")["items"][0]["status"], "answered")

    def test_concurrent_runs_write_separate_files(self):
        self.run_cmd("status", *self.who(), "--status", "working", "--task", "a")
        os.environ["AOR_RUN_ID"] = "other-run"
        self.run_cmd("status", *self.who("aor-agent-qa"), "--status", "working", "--task", "b")
        files = sorted(p.name for p in (self.root / "aor/room/events/2026-10-15").iterdir())
        self.assertEqual(files, ["other-run.jsonl", "test-run.jsonl"])
        self.assertEqual(len(self.run_cmd("state", "agents")["agents"]), 2)


    def test_fires_to_alert_until_marked_and_again_after_refire(self):
        self.run_cmd("fire", *self.who(), "--reason", "failed_build", "--detail", "main red", "--ref", "ci/1")
        quiet = self.run_cmd("digest", now="2026-10-15T23:30:00Z")
        self.assertFalse(quiet["send"])
        self.assertEqual([f["key"] for f in quiet["fires_to_alert"]], ["alpha|failed_build|ci/1"])
        bad = self.run_cmd("digest", "--mark-alerted", "alpha|failed_build|nope", expect=1)
        self.assertIn("no active fire", bad["error"])
        self.run_cmd("digest", "--mark-alerted", "alpha|failed_build|ci/1", "--channel", "C0C9F0ERP35")
        self.assertEqual(self.run_cmd("digest")["fires_to_alert"], [])
        self.run_cmd("ask", *self.who(), "--question", "Ship?")
        self.assertTrue(self.run_cmd("digest")["send"], "marking a fire must not open the batch window")
        self.run_cmd("fire", *self.who(), "--reason", "failed_build", "--clear", "--ref", "ci/1", now="2026-10-15T12:10:00Z")
        self.run_cmd("fire", *self.who(), "--reason", "failed_build", "--detail", "red again", "--ref", "ci/1", now="2026-10-15T12:20:00Z")
        self.assertEqual(len(self.run_cmd("digest", now="2026-10-15T12:21:00Z")["fires_to_alert"]), 1)



class ConfigTest(unittest.TestCase):
    def test_reads_the_aor_section_of_shared_config_over_legacy(self):
        import room_signal

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "_bmad" / "aor").mkdir(parents=True)
            (root / "_bmad" / "aor" / "config.yaml").write_text("aor_timezone: UTC\naor_quiet_hours: 22:00-06:00\n")
            (root / "_bmad" / "config.yaml").write_text(
                "output_folder: '{project-root}/_bmad-output'\naor:\n  name: AI Operations Room\n"
                "  aor_timezone: America/Sao_Paulo  # BRT\n  aor_blocker_fire_hours: 12\n")
            cfg = room_signal.load_config(root)
            self.assertEqual((cfg["aor_timezone"], cfg["aor_blocker_fire_hours"], cfg["aor_quiet_hours"]),
                             ("America/Sao_Paulo", "12", "22:00-06:00"))
            self.assertNotIn("name", cfg)

if __name__ == "__main__":
    unittest.main(verbosity=2)
