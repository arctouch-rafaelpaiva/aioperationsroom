#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Unit tests for slack_post.py (channel guard, fallback, Slack errors). Run: uv run scripts/tests/test_slack_post.py"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import slack_post  # noqa: E402


class FakeOpener:
    def __init__(self, reply: dict):
        self.reply, self.requests = reply, []

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        body = io.BytesIO(json.dumps(self.reply).encode())
        return contextlib.closing(body)


class SlackPostTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "_bmad/aor").mkdir(parents=True)
        (self.root / "_bmad/aor/config.yaml").write_text("aor_slack_channel: C0OPS\n")

    def tearDown(self):
        self.tmp.cleanup()

    def run_post(self, *argv, opener=None, token="xoxb-test"):
        buf = io.StringIO()
        env = {"AOR_SLACK_BOT_TOKEN": token} if token else {}
        with mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(buf):
            code = slack_post.main(["--root", str(self.root), *argv], opener=opener or FakeOpener({"ok": True}))
        return code, json.loads(buf.getvalue())

    def test_posts_markdown_block_in_thread(self):
        opener = FakeOpener({"ok": True, "channel": "C0OPS", "ts": "171.2"})
        code, out = self.run_post("--text", "**Morning.** Nothing needs you.", "--thread-ts", "171.1", opener=opener)
        self.assertEqual((code, out["ts"], out["thread_ts"]), (0, "171.2", "171.1"))
        sent = json.loads(opener.requests[0].data)
        self.assertEqual(sent["channel"], "C0OPS")
        self.assertEqual(sent["blocks"], [{"type": "markdown", "text": "**Morning.** Nothing needs you."}])
        self.assertEqual(opener.requests[0].get_header("Authorization"), "Bearer xoxb-test")

    def test_refuses_other_channels(self):
        opener = FakeOpener({"ok": True})
        code, out = self.run_post("--channel", "C0CLIENT", "--text", "hi", opener=opener)
        self.assertEqual(code, 1)
        self.assertIn("only to the operator channel", out["error"])
        self.assertEqual(opener.requests, [])

    def test_without_token_points_to_mcp_fallback(self):
        code, out = self.run_post("--text", "hi", token="")
        self.assertEqual((code, out["fallback"], out["channel"]), (1, "slack-mcp", "C0OPS"))

    def test_slack_error_carries_a_hint(self):
        code, out = self.run_post("--text", "hi", opener=FakeOpener({"ok": False, "error": "not_in_channel"}))
        self.assertEqual(code, 2)
        self.assertIn("/invite @Maestro", out["hint"])

    def test_oversized_message_is_refused(self):
        code, out = self.run_post("--text", "x" * (slack_post.MARKDOWN_BLOCK_LIMIT + 1))
        self.assertEqual(code, 1)
        self.assertIn("split it", out["error"])


if __name__ == "__main__":
    unittest.main()
