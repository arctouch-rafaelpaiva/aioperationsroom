#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""aor-agent-maestro: turn the operator's replies in a digest thread into aor-signal resolves.

Until the room's Slack app adds buttons, the operator answers in the digest thread:

  approve all                  every open approval the digest listed
  approve ap-12, ap-13         approve these
  reject ap-12: too early      reject an approval or an ask, with a reason
  edit ap-12: <new text>       approve with edited content
  answer q-7: <text>           answer an ask

One command per line; case-insensitive. Lines that aren't commands are returned as
`unparsed` so Maestro can read them as conversation.

Input (--thread FILE or - for stdin), built from the Slack MCP read of the thread:
  {"parent": {"ts": "...", "text": "<the digest>"},
   "replies": [{"user": "U...", "ts": "...", "text": "..."}]}
--state FILE is the output of `room_signal.py state items` (current item statuses).
--operator U... keeps only the operator's replies.

Each produced resolve carries --note slack:<reply ts>. Replies at or before the
newest such note already in state are skipped, so re-reading a thread every relay
run never applies a decision twice.

Output: JSON {ok, resolves: [argv for room_signal.py], skipped, unparsed}.
Exit codes: 0 ok, 1 invalid input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LEGAL = {
    ("approval", "approved"): ["open"],
    ("approval", "edited"): ["open", "approved", "edited"],
    ("approval", "rejected"): ["open", "approved", "edited"],
    ("ask", "answered"): ["open"],
    ("ask", "rejected"): ["open"],
}
ID = r"(?:ap|q)-[A-Za-z0-9-]+"
LINE = re.compile(rf"^\s*(approve|reject|edit|answer)\s+(all\b|{ID}(?:\s*,\s*{ID})*)\s*(?::\s*(.*))?$", re.I)


def ts_key(ts: str) -> float:
    try:
        return float(ts)
    except (TypeError, ValueError):
        return 0.0


def read_json(path: str):
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    return json.loads(text)


def parse(thread: dict, items: dict[str, dict], operator: str | None) -> dict:
    handled = [ts_key(m[1]) for i in items.values() if (m := re.match(r"^slack:(\S+)", str(i.get("note") or "")))]
    after = max(handled, default=0.0)
    listed = re.findall(ID, (thread.get("parent") or {}).get("text", ""))
    resolves, skipped, unparsed = [], [], []
    for reply in sorted(thread.get("replies") or [], key=lambda r: ts_key(r.get("ts"))):
        if operator and reply.get("user") != operator:
            continue
        if ts_key(reply.get("ts")) <= after:
            continue
        for raw in (reply.get("text") or "").splitlines():
            if not raw.strip():
                continue
            m = LINE.match(raw)
            if not m:
                unparsed.append({"ts": reply.get("ts"), "text": raw.strip()})
                continue
            verb, target, rest = m[1].lower(), m[2], (m[3] or "").strip()
            if target.lower().startswith("all"):
                if verb != "approve":
                    skipped.append({"line": raw.strip(), "reason": "only 'approve all' is supported"})
                    continue
                ids = [i for i in dict.fromkeys(listed) if items.get(i, {}).get("kind") == "approval"]
            else:
                ids = [i.strip() for i in target.split(",")]
            for iid in ids:
                item = items.get(iid)
                if not item:
                    skipped.append({"item": iid, "reason": "unknown item"})
                    continue
                kind = item["kind"]
                decision = {"approve": "approved", "edit": "edited", "answer": "answered", "reject": "rejected"}[verb]
                if (kind, decision) not in LEGAL:
                    skipped.append({"item": iid, "reason": f"'{verb}' does not apply to an {kind}"})
                    continue
                if item["status"] not in LEGAL[(kind, decision)]:
                    skipped.append({"item": iid, "reason": f"already {item['status']}"})
                    continue
                if decision in ("edited", "answered") and not rest:
                    skipped.append({"item": iid, "reason": f"'{verb}' needs text after a colon"})
                    continue
                note = f"slack:{reply.get('ts')}" + (f" {rest}" if decision == "rejected" and rest else "")
                argv = ["resolve", "--item", iid, "--decision", decision, "--by", "slack", "--note", note]
                if decision == "edited":
                    argv += ["--payload", rest]
                elif decision == "answered":
                    argv += ["--answer", rest]
                resolves.append(argv)
                item["status"] = decision
    return {"ok": True, "resolves": resolves, "skipped": skipped, "unparsed": unparsed}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--thread", required=True, help="thread JSON file, or - for stdin")
    p.add_argument("--state", required=True, help="output of `room_signal.py state items`")
    p.add_argument("--operator", help="Slack user id of the operator")
    args = p.parse_args(argv)
    try:
        thread = read_json(args.thread)
        state = read_json(args.state)
        items = {i["id"]: dict(i) for i in state.get("items", [])}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": f"bad input: {exc}"}))
        return 1
    print(json.dumps(parse(thread, items, args.operator), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
