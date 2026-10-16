#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Unit tests for project_memory.py. Run: uv run scripts/tests/test_project_memory.py"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import project_memory  # noqa: E402

NOW = "2026-10-16T11:00:00Z"


def make_project(root: Path, pid: str, status: str = "active") -> Path:
    base = root / "_bmad/memory/aor/projects" / pid
    base.mkdir(parents=True)
    (base / "project.yaml").write_text(f"schema: 1\nid: {pid}\nname: {pid.title()}\nstatus: {status}\n")
    (base / "index.md").write_text(f"# {pid}\n")
    return base


class ProjectMemoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        os.environ["AOR_RUN_ID"] = "run-1"
        self.base = make_project(self.root, "payments")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, *argv, expect=0, now=NOW, root=None):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = project_memory.main(["--root", str(root or self.root), "--now", now, *argv])
        self.assertEqual(code, expect, buf.getvalue())
        out = buf.getvalue()
        return json.loads(out) if out.lstrip().startswith("{") else out

    def test_log_goes_to_per_run_file_in_local_date(self):
        out = self.run_cmd("log", "--project", "payments", "--role", "pm", "--text", "Routed PAY-142\nto requirements", now="2026-10-17T01:30:00Z")
        self.assertEqual(out["file"], "_bmad/memory/aor/projects/payments/daily/2026-10-16/run-1.md")
        self.assertEqual(out["line"], "- 22:30 [pm] Routed PAY-142 to requirements")
        os.environ["AOR_RUN_ID"] = "run-2"
        self.run_cmd("log", "--project", "payments", "--role", "qa", "--text", "Scenarios drafted")
        self.assertEqual(len(list((self.base / "daily/2026-10-16").glob("*.md"))), 2)

    def test_inbox_dedupes_by_key_and_tracks_status(self):
        a = self.run_cmd("inbox", "add", "--project", "payments", "--title", "PAY-142 changed", "--source", "jira", "--key", "jira|PAY-142|t1")
        b = self.run_cmd("inbox", "add", "--project", "payments", "--title", "PAY-142 changed again", "--key", "jira|PAY-142|t1")
        self.assertTrue(a["created"])
        self.assertFalse(b["created"])
        self.assertEqual(a["item"]["id"], b["item"]["id"])
        iid = a["item"]["id"]
        bad = self.run_cmd("inbox", "set", "--project", "payments", "--id", iid, "--status", "routed", expect=1)
        self.assertIn("--role", bad["error"])
        self.run_cmd("inbox", "set", "--project", "payments", "--id", iid, "--status", "routed", "--role", "requirements")
        self.assertEqual(self.run_cmd("inbox", "list", "--project", "payments", "--status", "open")["items"][0]["role"], "requirements")
        self.run_cmd("inbox", "set", "--project", "payments", "--id", iid, "--status", "done", "--note", "Stories drafted")
        self.assertEqual(self.run_cmd("inbox", "list", "--project", "payments", "--status", "open")["items"], [])
        again = self.run_cmd("inbox", "set", "--project", "payments", "--id", iid, "--status", "new", expect=1)
        self.assertIn("already done", again["error"])

    def test_unknown_project_names_known_ones(self):
        out = self.run_cmd("log", "--project", "nope", "--role", "pm", "--text", "x", expect=1)
        self.assertIn("known: payments", out["error"])

    def test_context_reads_since_last_wrap(self):
        (self.base / "eod").mkdir()
        (self.base / "eod/2026-10-15.md").write_text("# Wrap 15\n- carry PAY-9")
        for day, text in [("2026-10-14", "old"), ("2026-10-15", "late on 15th"), ("2026-10-16", "today")]:
            (self.base / "daily" / day).mkdir(parents=True)
            (self.base / "daily" / day / "r.md").write_text(f"- 09:00 [pm] {text}")
        self.run_cmd("inbox", "add", "--project", "payments", "--title", "Open thing")
        md = self.run_cmd("context", "--project", "payments", "--format", "md")
        self.assertIn("carry PAY-9", md)
        self.assertIn("today", md)
        self.assertIn("late on 15th", md)
        self.assertNotIn("old", md)
        self.assertIn("inbox: 1 open", md)

    def test_active_projects_skip_archived(self):
        make_project(self.root, "alpha", status="archived")
        make_project(self.root, "beta")
        self.assertEqual(project_memory.active_projects(self.root), ["beta", "payments"])


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.remote = t / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.remote)], check=True)
        self.a, self.b = t / "a", t / "b"
        for clone in (self.a, self.b):
            subprocess.run(["git", "clone", "-q", str(self.remote), str(clone)], check=True, capture_output=True)
            for k, v in (("user.email", "t@example.com"), ("user.name", "t"), ("pull.rebase", "true")):
                subprocess.run(["git", "config", k, v], cwd=clone, check=True)
        make_project(self.a, "payments")
        (self.a / "README.md").write_text("ops\n")
        subprocess.run(["git", "add", "-A"], cwd=self.a, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.a, check=True)
        subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], cwd=self.a, check=True, capture_output=True)
        subprocess.run(["git", "branch", "--set-upstream-to=origin/main"], cwd=self.a, check=True, capture_output=True)
        subprocess.run(["git", "pull", "-q"], cwd=self.b, check=True, capture_output=True)

    def tearDown(self):
        self.tmp.cleanup()

    def sync(self, root: Path, run: str, expect=0):
        os.environ["AOR_RUN_ID"] = run
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            project_memory.main(["--root", str(root), "--now", NOW, "log", "--project", "payments", "--role", "pm", "--text", run])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = project_memory.main(["--root", str(root), "sync", "--project", "payments", "--message", f"aor payments: {run}"])
        self.assertEqual(code, expect, buf.getvalue())
        return json.loads(buf.getvalue())

    def test_concurrent_runs_both_land(self):
        out_a = self.sync(self.a, "run-a")
        out_b = self.sync(self.b, "run-b")
        self.assertTrue(out_a["pushed"] and out_b["pushed"])
        subprocess.run(["git", "pull", "-q"], cwd=self.a, check=True, capture_output=True)
        logs = sorted(p.name for p in (self.a / "_bmad/memory/aor/projects/payments/daily/2026-10-16").glob("*.md"))
        self.assertEqual(logs, ["run-a.md", "run-b.md"])

    def test_conflict_is_reported_not_pushed(self):
        for clone, text in ((self.a, "A"), (self.b, "B")):
            (clone / "_bmad/memory/aor/projects/payments/index.md").write_text(f"# {text}\n")
        self.sync(self.a, "run-a")
        out = self.sync(self.b, "run-b", expect=2)
        self.assertIn("rebase conflict", out["error"])
        self.assertIn("_bmad/memory/aor/projects/payments/index.md", out["conflicts"])

    def test_maestro_syncs_several_projects_and_its_sanctum(self):
        make_project(self.a, "beta")
        os.environ["AOR_RUN_ID"] = "relay-1"
        sanctum = self.a / "_bmad/memory/aor-agent-maestro"
        sanctum.mkdir(parents=True)
        (sanctum / "MEMORY.md").write_text("# Memory\n")
        for pid in ("payments", "beta"):
            with contextlib.redirect_stdout(io.StringIO()):
                project_memory.main(["--root", str(self.a), "--now", NOW, "inbox", "add", "--project", pid, "--title", "Client mail", "--from", "maestro"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = project_memory.main(["--root", str(self.a), "sync", "--project", "payments", "--project", "beta",
                                        "--sanctum", "aor-agent-maestro", "--message", "aor maestro: relay", "--no-push"])
        self.assertEqual(code, 0, buf.getvalue())
        files = json.loads(buf.getvalue())["files"]
        self.assertTrue(any("projects/beta/inbox/" in f for f in files))
        self.assertTrue(any("projects/payments/inbox/" in f for f in files))
        self.assertIn("_bmad/memory/aor-agent-maestro/MEMORY.md", files)

    def test_sync_needs_a_project_or_a_cross_project_sanctum(self):
        sanctum = self.a / "_bmad/memory/aor-agent-maestro"
        sanctum.mkdir(parents=True)
        (sanctum / "MEMORY.md").write_text("# Memory\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = project_memory.main(["--root", str(self.a), "sync", "--sanctum", "aor-agent-maestro", "--message", "relay", "--no-push"])
        self.assertEqual(code, 0, buf.getvalue())
        self.assertEqual(json.loads(buf.getvalue())["files"], ["_bmad/memory/aor-agent-maestro/MEMORY.md"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = project_memory.main(["--root", str(self.a), "sync", "--message", "pm", "--no-push"])
        self.assertNotEqual(code, 0)
        self.assertIn("needs --project", buf.getvalue())

    def test_nothing_to_commit_still_ok(self):
        os.environ["AOR_RUN_ID"] = "noop"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = project_memory.main(["--root", str(self.a), "sync", "--project", "payments", "--message", "noop", "--no-push"])
        self.assertEqual(code, 0)
        self.assertIsNone(json.loads(buf.getvalue())["committed"])

if __name__ == "__main__":
    unittest.main()
