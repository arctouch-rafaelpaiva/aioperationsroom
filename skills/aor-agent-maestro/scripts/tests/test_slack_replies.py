#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Unit tests for slack_replies.py (commands, legality, idempotency). Run: uv run scripts/tests/test_slack_replies.py"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import slack_replies  # noqa: E402

OP = "U0OP"
AP1, AP2, Q1 = "ap-20261016100000-aaaaaa", "ap-20261016100500-bbbbbb", "q-20261016101000-cccccc"


def items(**status):
    base = {AP1: ("approval", "open"), AP2: ("approval", "open"), Q1: ("ask", "open")}
    out = {}
    for iid, (kind, st) in base.items():
        out[iid] = {"id": iid, "kind": kind, "status": st}
    for iid, st in status.items():
        out[iid.replace("_", "-")]["status"] = st
    return out


def thread(*replies, user=OP):
    return {"parent": {"ts": "100.0", "text": f"Payments: {AP1} post notes. Atlas: {AP2} comment. {Q1} ship Friday?"},
            "replies": [{"user": user, "ts": ts, "text": text} for ts, text in replies]}


class SlackRepliesTest(unittest.TestCase):
    def test_approve_all_covers_listed_approvals_only(self):
        out = slack_replies.parse(thread(("101.0", "Approve all")), items(), OP)
        self.assertEqual([r[2] for r in out["resolves"]], [AP1, AP2])
        self.assertTrue(all(r[r.index("--note") + 1] == "slack:101.0" for r in out["resolves"]))

    def test_each_command_builds_the_right_resolve(self):
        text = f"reject {AP1}: too early\nedit {AP2}: Ship notes v2\nanswer {Q1}: Friday\nthanks!"
        out = slack_replies.parse(thread(("101.0", text)), items(), OP)
        by_item = {r[2]: r for r in out["resolves"]}
        self.assertEqual(by_item[AP1][4], "rejected")
        self.assertIn("slack:101.0 too early", by_item[AP1])
        self.assertEqual(by_item[AP2][-2:], ["--payload", "Ship notes v2"])
        self.assertEqual(by_item[Q1][-2:], ["--answer", "Friday"])
        self.assertEqual(out["unparsed"], [{"ts": "101.0", "text": "thanks!"}])

    def test_illegal_and_unknown_are_skipped_with_reasons(self):
        out = slack_replies.parse(thread(("101.0", f"approve {Q1}, ap-nope\nanswer {AP1}: yes\nedit {AP2}")), items(), OP)
        self.assertEqual(out["resolves"], [])
        reasons = " | ".join(s["reason"] for s in out["skipped"])
        for fragment in ("does not apply to an ask", "unknown item", "does not apply to an approval", "needs text"):
            self.assertIn(fragment, reasons)

    def test_handled_replies_and_other_users_are_ignored(self):
        state = items()
        state[AP1].update(status="approved", note="slack:101.0")
        replies = thread(("101.0", f"approve {AP1}"), ("102.0", f"approve {AP2}"))
        replies["replies"].append({"user": "U0CLIENT", "ts": "103.0", "text": f"answer {Q1}: never"})
        out = slack_replies.parse(replies, state, OP)
        self.assertEqual([r[2] for r in out["resolves"]], [AP2])

    def test_second_decision_on_same_item_in_one_run_respects_new_status(self):
        out = slack_replies.parse(thread(("101.0", f"approve {AP1}"), ("102.0", f"approve {AP1}")), items(), OP)
        self.assertEqual(len(out["resolves"]), 1)
        self.assertEqual(out["skipped"][0]["reason"], "already approved")


if __name__ == "__main__":
    unittest.main()
