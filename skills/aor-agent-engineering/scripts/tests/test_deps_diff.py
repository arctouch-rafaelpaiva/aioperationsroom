#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Unit tests for deps_diff.py. Run: uv run scripts/tests/test_deps_diff.py"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deps_diff  # noqa: E402


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = deps_diff.main(argv)
    return code, json.loads(buf.getvalue())


class ParseTest(unittest.TestCase):
    def test_parsers(self):
        npm = deps_diff.parse("package.json", json.dumps({"dependencies": {"react": "^18.2.0"}, "devDependencies": {"vitest": "1.0.0"}}))
        self.assertEqual(npm, {"react": "^18.2.0", "vitest (dev)": "1.0.0"})
        req = deps_diff.parse("requirements.txt", "# pinned\nDjango==4.2.1\nrequests[socks]>=2.31 ; python_version>'3.8'\n-r base.txt\n")
        self.assertEqual(req, {"django": "==4.2.1", "requests": ">=2.31"})
        py = deps_diff.parse("pyproject.toml", '[project]\ndependencies = ["httpx>=0.27"]\n[project.optional-dependencies]\ntest = ["pytest>=8"]\n')
        self.assertEqual(py, {"httpx": ">=0.27", "pytest (test)": ">=8"})
        go = deps_diff.parse("go.mod", "module x\nrequire github.com/a/b v1.2.0\nrequire (\n\tgithub.com/c/d v0.3.1 // indirect\n)\n")
        self.assertEqual(go, {"github.com/a/b": "v1.2.0", "github.com/c/d": "v0.3.1"})
        cargo = deps_diff.parse("Cargo.toml", '[dependencies]\nserde = { version = "1.0" }\n[dev-dependencies]\ntokio = "1"\n')
        self.assertEqual(cargo, {"serde": "1.0", "tokio (dev)": "1"})

    def test_major_detection(self):
        d = deps_diff.diff("package.json", {"a": "^4.1.0", "b": "0.3.0", "c": "1.2.0", "gone": "1"}, {"a": "5.0.0", "b": "0.4.0", "c": "1.9.0", "new": "2"})
        self.assertEqual([c["major"] for c in d["changed"]], [True, True, False])
        self.assertEqual((d["added"][0]["name"], d["removed"][0]["name"]), ("new", "gone"))

    def test_bad_manifest_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "package.json").write_text("{nope")
            self.assertEqual(run(["files", "--base", str(Path(tmp, "old.json")), "--head", str(Path(tmp, "package.json"))])[0], 2)
            self.assertEqual(run(["files", "--base", "a.txt", "--head", "b.txt"])[0], 2)


class GitModeTest(unittest.TestCase):
    def test_diffs_manifests_between_refs(self):
        with tempfile.TemporaryDirectory() as repo:
            g = lambda *a: subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True)
            g("init", "-q", "-b", "main")
            g("config", "user.email", "t@t")
            g("config", "user.name", "t")
            Path(repo, "package.json").write_text(json.dumps({"dependencies": {"stripe": "^4.0.0"}}))
            Path(repo, "README.md").write_text("x")
            g("add", ".")
            g("commit", "-qm", "base")
            g("checkout", "-qb", "feature")
            Path(repo, "package.json").write_text(json.dumps({"dependencies": {"stripe": "^5.0.0", "zod": "3.23.0"}}))
            Path(repo, "api").mkdir()
            Path(repo, "api/requirements.txt").write_text("fastapi==0.111\n")
            g("add", ".")
            g("commit", "-qm", "bump")
            code, out = run(["git", "--repo", repo, "--base", "main", "--head", "feature"])
            self.assertEqual(code, 0)
            self.assertEqual(out["major"], ["package.json: stripe ^4.0.0 -> ^5.0.0"])
            self.assertEqual(out["summary"], "2 added, 0 removed, 1 changed (1 major)")
            self.assertEqual([m["path"] for m in out["manifests"]], ["api/requirements.txt", "package.json"])
            self.assertEqual(run(["git", "--repo", repo, "--base", "main", "--head", "main"])[1]["summary"], "no dependency changes")
            self.assertEqual(run(["git", "--repo", repo, "--base", "main", "--head", "ghost"])[0], 2)


if __name__ == "__main__":
    unittest.main()
