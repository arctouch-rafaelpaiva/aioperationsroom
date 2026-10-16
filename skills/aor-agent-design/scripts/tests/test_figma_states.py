#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Unit tests for figma_states.py (no network). Run: uv run scripts/tests/test_figma_states.py"""

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
import figma_states  # noqa: E402

FRAMES = [
    {"id": "1:1", "name": "Refund request"},
    {"id": "1:2", "name": "Refund request / Loading"},
    {"id": "1:3", "name": "Refund request – Failed"},
    {"id": "1:4", "name": "Refund request / Over limit"},
    {"id": "2:1", "name": "Order detail / Empty"},
    {"id": "3:1", "name": "Settings"},
]
SPEC = {"story": "PAY-142", "screens": [
    {"name": "Refund request", "states": ["default", "loading", "error", "success", "over limit"]},
    {"name": "Order history", "match": ["order detail"], "states": ["default", "empty"]},
]}


class CheckTest(unittest.TestCase):
    def test_states_found_missing_and_unclaimed(self):
        out = figma_states.check(SPEC, FRAMES)
        refund, orders = out["screens"]
        self.assertEqual(refund["found"], {"default": ["1:1"], "loading": ["1:2"], "error": ["1:3"], "over limit": ["1:4"]})
        self.assertEqual(refund["missing"], ["success"])
        self.assertEqual((orders["found"], orders["missing"]), ({"empty": ["2:1"]}, ["default"]))
        self.assertEqual((out["ok"], out["missing_states"], out["unclaimed_frames"]), (False, 2, ["Settings"]))

    def test_bad_spec(self):
        with self.assertRaises(figma_states.BadInput):
            figma_states.check({"screens": [{"name": "X"}]}, FRAMES)


class FigmaApiTest(unittest.TestCase):
    def test_url_parsing_and_links(self):
        self.assertEqual(figma_states.parse_url("https://www.figma.com/design/AbC123/Pay?node-id=12-34&t=x"), ("AbC123", "12:34"))
        self.assertEqual(figma_states.parse_url("https://www.figma.com/file/AbC123/Pay"), ("AbC123", None))
        with self.assertRaises(figma_states.BadInput):
            figma_states.parse_url("https://example.com/design/x")
        self.assertEqual(figma_states.link("K", "1:2"), "https://www.figma.com/design/K/?node-id=1-2")

    def test_frames_from_file_and_comment_body(self):
        data = {"document": {"children": [
            {"name": "Payments", "children": [{"id": "1:1", "type": "FRAME", "name": "Refund"}, {"id": "1:9", "type": "TEXT", "name": "note"}]},
            {"name": "Archive", "children": [{"id": "5:1", "type": "SECTION", "name": "Old"}]}]}}
        frames = figma_states.frames_from_file(data, "K", page="Payments")
        self.assertEqual(frames, [{"id": "1:1", "name": "Refund", "page": "Payments", "link": "https://www.figma.com/design/K/?node-id=1-1"}])
        self.assertEqual(len(figma_states.frames_from_file(data, "K")), 2)
        self.assertEqual(figma_states.comment_body("Hi", "1:1"), {"message": "Hi", "client_meta": {"node_id": "1:1", "node_offset": {"x": 0, "y": 0}}})
        self.assertEqual(figma_states.comment_body("Hi", None), {"message": "Hi"})

    def test_cli_needs_token_and_check_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec, frames = Path(tmp, "s.yaml"), Path(tmp, "f.json")
            spec.write_text("story: PAY-142\nscreens:\n  - name: Refund request\n    states: [default, loading]\n")
            frames.write_text(json.dumps(FRAMES))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(figma_states.main(["check", "--spec", str(spec), "--frames", str(frames)]), 0)
            self.assertTrue(json.loads(buf.getvalue())["ok"])
            buf = io.StringIO()
            with mock.patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(buf):
                self.assertEqual(figma_states.main(["frames", "--url", "https://www.figma.com/design/K/x"]), 2)
            self.assertIn("FIGMA_TOKEN", json.loads(buf.getvalue())["error"])


if __name__ == "__main__":
    unittest.main()
