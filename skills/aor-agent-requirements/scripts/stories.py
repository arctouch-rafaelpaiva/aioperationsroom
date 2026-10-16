#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""aor-agent-requirements: check a story draft, and build the exact Jira payload from it.

The draft format is defined in references/story-format.md: frontmatter (jira_project,
epic?, ac_format?, labels?, max_ac?), an optional `# Epic: <title>` with its
description, then `## Story: <title>` blocks with a user-story line and `###`
sections (Acceptance criteria, Business rules, Edge cases, Dependencies, Out of
scope, Open questions).

  check    structure, AC format (Given/When/Then or checklist), vague wording, size,
           and readiness (a story with open questions is not ready)
  payload  the JSON to pass to aor-signal `approval --payload-file`: one batch that
           creates the epic (unless frontmatter names an existing one) and its stories.
           Refused while check has errors.

Usage:
  uv run stories.py check --file <draft.md>
  uv run stories.py payload --file <draft.md> [--out <payload.json>]

Output: JSON. Exit codes: 0 ok, 1 the draft has errors, 2 unreadable input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SECTIONS = {
    "acceptance criteria": "ac",
    "business rules": "rules",
    "edge cases": "edges",
    "dependencies": "deps",
    "out of scope": "out",
    "open questions": "questions",
}
SECTION_TITLES = {v: k.capitalize() for k, v in SECTIONS.items()}
USER_STORY = re.compile(r"\bas an?\b.+?\bi want\b.+?\bso that\b.+", re.I | re.S)
GWT = re.compile(r"^\s*given\b.+\bwhen\b.+\bthen\b.+", re.I | re.S)
VAGUE = ["works as expected", "work as expected", "properly", "correctly", "user-friendly", "user friendly", "intuitive",
         "seamless", "fast", "quickly", "etc", "and/or", "as needed", "should work", "handles errors", "appropriate"]
JIRA_KEY = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
LIST_ITEM = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.*)$")


def split_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m[1].splitlines():
        line = line.split(" #", 1)[0].rstrip()
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip("'\"")
    return meta, text[m.end():]


def list_items(lines: list[str]) -> list[str]:
    items: list[str] = []
    for line in lines:
        m = LIST_ITEM.match(line)
        if m:
            items.append(m[1].strip())
        elif line.strip() and items:
            items[-1] += " " + line.strip()
    return items


def parse(text: str) -> dict:
    meta, body = split_frontmatter(text)
    draft = {"meta": meta, "epic": None, "stories": []}
    current, section = None, None
    for line in body.splitlines():
        if m := re.match(r"^#\s+Epic:\s*(.+)$", line):
            draft["epic"] = {"title": m[1].strip(), "body": []}
            current, section = draft["epic"], "body"
        elif m := re.match(r"^##\s+Story:\s*(.+)$", line):
            current = {"title": m[1].strip(), "body": [], **{k: [] for k in SECTIONS.values()}}
            draft["stories"].append(current)
            section = "body"
        elif (m := re.match(r"^###\s+(.+?)\s*$", line)) and current is not None and current is not draft["epic"]:
            section = SECTIONS.get(m[1].lower())
            if section is None:
                current.setdefault("unknown_sections", []).append(m[1])
        elif current is not None and section:
            current[section].append(line)
    for story in draft["stories"]:
        story["user_story"] = " ".join(l.strip() for l in story["body"] if l.strip())
        for key in SECTIONS.values():
            story[key] = list_items(story[key])
    if draft["epic"]:
        draft["epic"]["description"] = "\n".join(draft["epic"].pop("body")).strip()
    return draft


def check(draft: dict) -> dict:
    meta, errors, warnings, report = draft["meta"], [], [], []
    if not re.fullmatch(r"[A-Z][A-Z0-9]+", meta.get("jira_project", "")):
        errors.append("frontmatter needs jira_project: the Jira project key, e.g. PAY")
    epic_key = meta.get("epic", "")
    if epic_key and not JIRA_KEY.fullmatch(epic_key):
        errors.append(f"frontmatter epic '{epic_key}' is not a Jira key; omit it to create a new epic")
    if not epic_key and not draft["epic"]:
        errors.append("add '# Epic: <title>' with a description, or name an existing epic in frontmatter (epic: PAY-12)")
    if draft["epic"] and not epic_key and not draft["epic"]["description"]:
        errors.append("the new epic needs a description under its heading")
    fmt = meta.get("ac_format", "gwt").lower()
    if fmt not in ("gwt", "checklist"):
        errors.append(f"ac_format '{fmt}' is unknown; use gwt or checklist")
    max_ac = int(meta.get("max_ac", "8") or 8)
    if not draft["stories"]:
        errors.append("no stories: add '## Story: <title>' blocks")
    titles = [s["title"].lower() for s in draft["stories"]]
    for dup in sorted({t for t in titles if titles.count(t) > 1}):
        errors.append(f"two stories share the title '{dup}'")
    for s in draft["stories"]:
        where = f"story '{s['title']}'"
        for name in s.get("unknown_sections", []):
            warnings.append(f"{where}: unknown section '### {name}' is left out of the payload")
        if not USER_STORY.search(s["user_story"]):
            errors.append(f"{where}: needs a user-story line (As a …, I want …, so that …)")
        if not s["ac"]:
            errors.append(f"{where}: no acceptance criteria")
        for i, ac in enumerate(s["ac"], 1):
            if fmt == "gwt" and not GWT.match(ac):
                errors.append(f"{where}: AC {i} is not Given/When/Then: {ac[:80]}")
            lowered = f" {ac.lower()} "
            hits = [w for w in VAGUE if re.search(rf"(?<![\w-]){re.escape(w)}(?![\w-])", lowered)]
            if hits:
                warnings.append(f"{where}: AC {i} is vague ({', '.join(hits)}); say what the user sees or how much")
        if len(s["ac"]) > max_ac:
            warnings.append(f"{where}: {len(s['ac'])} AC (limit {max_ac}); consider splitting")
        report.append({"title": s["title"], "ac": len(s["ac"]), "rules": len(s["rules"]), "edge_cases": len(s["edges"]),
                       "dependencies": sorted(set(JIRA_KEY.findall(" ".join(s["deps"])))),
                       "open_questions": s["questions"], "ready": not s["questions"]})
    return {"ok": not errors, "errors": errors, "warnings": warnings, "stories": report,
            "ready": sum(r["ready"] for r in report), "not_ready": sum(not r["ready"] for r in report)}


def story_description(s: dict) -> str:
    out = [s["user_story"]]
    for key in ("ac", "rules", "edges", "deps", "out", "questions"):
        if s[key]:
            numbered = key == "ac"
            out += ["", f"**{SECTION_TITLES[key]}**", *[f"{i}. {x}" if numbered else f"- {x}" for i, x in enumerate(s[key], 1)]]
    return "\n".join(out)


def payload(draft: dict) -> dict:
    meta = draft["meta"]
    labels = [l.strip() for l in meta.get("labels", "").split(",") if l.strip()]
    epic = {"key": meta["epic"]} if meta.get("epic") else {"summary": draft["epic"]["title"], "description": draft["epic"]["description"]}
    issues = [{"type": "Story", "summary": s["title"], "description": story_description(s), "labels": labels} for s in draft["stories"]]
    return {"target": "jira", "action": "create_issues", "project_key": meta["jira_project"], "epic": epic,
            "issues": issues, "content_format": "markdown"}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["check", "payload"])
    p.add_argument("--file", required=True, help="the story draft (markdown)")
    p.add_argument("--out", help="payload: also write the JSON here")
    args = p.parse_args(argv)
    try:
        draft = parse(Path(args.file).read_text(encoding="utf-8"))
    except OSError as exc:
        print(json.dumps({"ok": False, "error": f"cannot read draft: {exc}"}))
        return 2
    result = check(draft)
    if args.cmd == "check" or not result["ok"]:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    body = payload(draft)
    if args.out:
        Path(args.out).write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    preview = f"Create {'epic + ' if 'summary' in body['epic'] else ''}{len(body['issues'])} stories in {body['project_key']}"
    print(json.dumps({"ok": True, "preview": preview, "warnings": result["warnings"], "not_ready": result["not_ready"],
                      "payload": body}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
