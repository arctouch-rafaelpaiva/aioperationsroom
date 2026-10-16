#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""aor-agent-design: check that designs draw every state a story needs, and talk to Figma's REST API.

  check     a state spec (YAML) against a frame list (JSON), and report each screen's
            states found (with frame links) and missing, plus frames no screen claims.
  frames    list a Figma file's pages and top-level frames as JSON   (needs FIGMA_TOKEN)
  comments  list a file's unresolved comments as JSON                (needs FIGMA_TOKEN)
  comment   post one comment, pinned to the url's node-id if it has one (needs FIGMA_TOKEN)

The frame list for check comes from `frames`, or from the Figma MCP in the same shape:
[{"id": "1:2", "name": "Refund request / Error", "page": "Payments", "link": "..."}].

State spec (references/state-review.md):
  story: PAY-142
  screens:
    - name: Refund request
      match: [refund request]         # optional: words in frame names for this screen
      states: [default, loading, error, success, over limit]

Built-in states match their synonyms in frame names (error: failed, failure, invalid…;
empty: no data, no results…). A screen's frame with no state word counts as default.
Any other state matches its own words.

Usage:
  uv run figma_states.py check --spec <states.yaml> --frames <frames.json>
  uv run figma_states.py frames --url <figma file url> [--page <name>]
  uv run figma_states.py comments --url <figma file url>
  uv run figma_states.py comment --url <figma url with node-id> --message-file <file>

Exit codes: 0 ok (check reports gaps in its JSON), 2 bad input, missing token, or API error.
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

import yaml

API = "https://api.figma.com/v1"
SYNONYMS = {
    "default": ["default", "idle", "initial", "filled", "base"],
    "loading": ["loading", "skeleton", "spinner", "progress", "pending"],
    "empty": ["empty", "no data", "no results", "zero state", "blank"],
    "error": ["error", "failure", "failed", "invalid", "problem"],
    "success": ["success", "done", "confirmation", "confirmed", "complete"],
    "disabled": ["disabled", "inactive"],
    "offline": ["offline", "no connection"],
}
ALL_STATE_WORDS = sorted({w for ws in SYNONYMS.values() for w in ws}, key=len, reverse=True)


class BadInput(Exception):
    pass


def norm(text: str) -> str:
    return " " + re.sub(r"\s+", " ", re.sub(r"[/\\|_\-–—.,:;()\[\]]+", " ", text.lower())).strip() + " "


def has(name: str, phrase: str) -> bool:
    return norm(phrase) in name


def check(spec: dict, frames: list[dict]) -> dict:
    if not isinstance(spec.get("screens"), list) or not spec["screens"]:
        raise BadInput("spec needs screens: a list of {name, states}")
    claimed, screens = set(), []
    for screen in spec["screens"]:
        name = str(screen.get("name", "")).strip()
        states = [str(s).strip().lower() for s in screen.get("states") or []]
        if not name or not states:
            raise BadInput(f"screen '{name or '?'}' needs a name and states")
        terms = [str(m) for m in screen.get("match") or [name]]
        found: dict[str, list[str]] = {s: [] for s in states}
        for f in frames:
            fname = norm(f"{f.get('name', '')}")
            if not any(has(fname, t) for t in terms):
                continue
            claimed.add(f.get("id"))
            rest = fname
            for t in terms:
                rest = rest.replace(norm(t), " ")
            ref = f.get("link") or f.get("id") or f.get("name")
            hit = False
            for s in states:
                if any(has(rest, w) for w in SYNONYMS.get(s, [s])):
                    found[s].append(ref)
                    hit = True
            if not hit and "default" in found and not any(has(rest, w) for w in ALL_STATE_WORDS):
                found["default"].append(ref)
        screens.append({"name": name, "found": {k: v for k, v in found.items() if v},
                        "missing": [s for s, v in found.items() if not v]})
    unclaimed = [f.get("name") for f in frames if f.get("id") not in claimed]
    missing = sum(len(s["missing"]) for s in screens)
    return {"ok": missing == 0, "story": spec.get("story", ""), "screens": screens, "missing_states": missing,
            "unclaimed_frames": unclaimed}


def parse_url(url: str) -> tuple[str, str | None]:
    m = re.match(r"^https://(?:www\.)?figma\.com/(?:file|design|proto|board)/([A-Za-z0-9]+)", url)
    if not m:
        raise BadInput("not a Figma file url (https://www.figma.com/design/<key>/...)")
    node = re.search(r"[?&]node-id=([0-9]+[-:][0-9]+)", url)
    return m[1], node[1].replace("-", ":") if node else None


def link(key: str, node_id: str) -> str:
    return f"https://www.figma.com/design/{key}/?node-id={node_id.replace(':', '-')}"


def frames_from_file(data: dict, key: str, page: str | None = None) -> list[dict]:
    out = []
    for p in (data.get("document") or {}).get("children") or []:
        if page and p.get("name") != page:
            continue
        for n in p.get("children") or []:
            if n.get("type") in ("FRAME", "COMPONENT", "COMPONENT_SET", "SECTION"):
                out.append({"id": n["id"], "name": n.get("name", ""), "page": p.get("name", ""), "link": link(key, n["id"])})
    return out


def comment_body(message: str, node_id: str | None) -> dict:
    body = {"message": message}
    if node_id:
        body["client_meta"] = {"node_id": node_id, "node_offset": {"x": 0, "y": 0}}
    return body


def api(path: str, body: dict | None = None) -> dict:
    token = os.environ.get("FIGMA_TOKEN")
    if not token:
        raise BadInput("FIGMA_TOKEN is not set; use the Figma MCP, or add the token as a secret")
    req = urllib.request.Request(f"{API}{path}", headers={"X-Figma-Token": token, "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None,
                                 method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.load(res)
    except urllib.error.HTTPError as exc:
        raise BadInput(f"Figma API {exc.code}: {exc.read().decode(errors='replace')[:300]}") from exc
    except urllib.error.URLError as exc:
        raise BadInput(f"Figma API unreachable: {exc.reason}") from exc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["check", "frames", "comments", "comment"])
    p.add_argument("--spec")
    p.add_argument("--frames")
    p.add_argument("--url")
    p.add_argument("--page")
    p.add_argument("--message-file")
    args = p.parse_args(argv)
    try:
        if args.cmd == "check":
            if not (args.spec and args.frames):
                raise BadInput("check needs --spec and --frames")
            spec = yaml.safe_load(Path(args.spec).read_text(encoding="utf-8")) or {}
            frames = json.loads(Path(args.frames).read_text(encoding="utf-8"))
            if not isinstance(frames, list):
                raise BadInput("frames must be a JSON list")
            out = check(spec, frames)
        else:
            if not args.url:
                raise BadInput(f"{args.cmd} needs --url")
            key, node = parse_url(args.url)
            if args.cmd == "frames":
                out = {"ok": True, "frames": frames_from_file(api(f"/files/{key}?depth=2"), key, args.page)}
            elif args.cmd == "comments":
                data = api(f"/files/{key}/comments")
                out = {"ok": True, "comments": [
                    {"id": c["id"], "message": c.get("message", ""), "user": (c.get("user") or {}).get("handle", ""),
                     "created_at": c.get("created_at", ""), "node_id": (c.get("client_meta") or {}).get("node_id"),
                     "reply_to": c.get("parent_id") or None}
                    for c in data.get("comments", []) if not c.get("resolved_at")]}
            else:
                if not args.message_file:
                    raise BadInput("comment needs --message-file")
                res = api(f"/files/{key}/comments", comment_body(Path(args.message_file).read_text(encoding="utf-8").strip(), node))
                out = {"ok": True, "comment_id": res.get("id"), "link": link(key, node) if node else f"https://www.figma.com/design/{key}/"}
    except (BadInput, OSError, ValueError, yaml.YAMLError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
