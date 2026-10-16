#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""aor-agent-maestro: post to the operator's Slack channel as the Maestro bot.

Uses chat.postMessage with AOR_SLACK_BOT_TOKEN (scope chat:write), sending the text
as a Slack `markdown` block so the same markdown works here and in the Slack MCP
fallback. Maestro posts only to the operator channel (aor_slack_channel); this
script refuses any other channel.

Without the token it exits 1 with "fallback": "slack-mcp": post the same text
through the Slack MCP instead (it posts as the operator, so they get no
notification) and say so in the next brief.

Usage:
  uv run slack_post.py --root <ops repo> (--text T | --text-file F) [--thread-ts TS]

Output: JSON {ok, channel, ts, thread_ts}. Exit codes: 0 posted, 1 invalid or no
token (see fallback), 2 Slack or network error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://slack.com/api/chat.postMessage"
DEFAULT_CHANNEL = "C0C9F0ERP35"
MARKDOWN_BLOCK_LIMIT = 12000


def operator_channel(root: Path) -> str:
    cfg = root / "_bmad" / "aor" / "config.yaml"
    if cfg.is_file():
        m = re.search(r"^aor_slack_channel\s*:\s*['\"]?([A-Z0-9]+)", cfg.read_text(encoding="utf-8"), re.M)
        if m:
            return m[1]
    return DEFAULT_CHANNEL


def post(token: str, channel: str, text: str, thread_ts: str | None, opener=urllib.request.urlopen) -> dict:
    body = {"channel": channel, "text": text[:3000], "blocks": [{"type": "markdown", "text": text}], "unfurl_links": False}
    if thread_ts:
        body["thread_ts"] = thread_ts
    req = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"})
    with opener(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main(argv: list[str] | None = None, opener=urllib.request.urlopen) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".")
    p.add_argument("--channel", help="must equal aor_slack_channel; defaults to it")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--text-file")
    p.add_argument("--thread-ts", help="reply in this thread (e.g. today's brief)")
    args = p.parse_args(argv)

    allowed = operator_channel(Path(args.root))
    channel = args.channel or allowed
    text = args.text if args.text is not None else Path(args.text_file).read_text(encoding="utf-8")

    def out(obj: dict, code: int) -> int:
        print(json.dumps(obj, ensure_ascii=False))
        return code

    if channel != allowed:
        return out({"ok": False, "error": f"Maestro posts only to the operator channel {allowed}; anything else needs an aor-signal approval"}, 1)
    if not text.strip():
        return out({"ok": False, "error": "empty message"}, 1)
    if len(text) > MARKDOWN_BLOCK_LIMIT:
        return out({"ok": False, "error": f"message is {len(text)} chars; split it under {MARKDOWN_BLOCK_LIMIT} (e.g. thread the details)"}, 1)
    token = os.environ.get("AOR_SLACK_BOT_TOKEN", "")
    if not token:
        return out({"ok": False, "fallback": "slack-mcp", "channel": channel,
                    "error": "AOR_SLACK_BOT_TOKEN not set; post through the Slack MCP (as the operator, no notification)"}, 1)
    try:
        res = post(token, channel, text, args.thread_ts, opener)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return out({"ok": False, "error": f"Slack unreachable: {exc}"}, 2)
    if not res.get("ok"):
        hint = {"not_in_channel": "invite the bot: /invite @Maestro", "invalid_auth": "the bot token is wrong or revoked",
                "missing_scope": "add chat:write to the Slack app and reinstall"}.get(res.get("error"), "")
        return out({"ok": False, "error": f"Slack error: {res.get('error')}", "hint": hint}, 2)
    return out({"ok": True, "channel": res.get("channel", channel), "ts": res.get("ts"), "thread_ts": args.thread_ts}, 0)


if __name__ == "__main__":
    sys.exit(main())
