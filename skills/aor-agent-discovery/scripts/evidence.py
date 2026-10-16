#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""aor-agent-discovery: keep the evidence ledger honest and weigh themes by rules anyone can read.

Ledger (YAML, references/evidence-ledger.md): `goals:` (id: description), `themes:`
(id: {name, goal}), and `evidence:` entries {id, date, source, ref, who, segment,
quote, themes}.

  check   ids unique, dates ISO, source one of the known kinds, quote and ref present,
          every theme defined and every theme's goal defined; personal data (emails,
          phone numbers) in who or quote is an error.
  themes  rank themes from evidence (optionally --since a date):
            people    distinct `who` values      channels  distinct `source` kinds
            mentions  entries                    segments, first and last seen, goal
          strength: strong (3+ people across 2+ channels), emerging (2+ people),
          anecdote (1 person). Sorted by people, then channels, then mentions, then
          last seen. Untagged evidence is counted.

Usage:
  uv run evidence.py check --file <evidence.yaml>
  uv run evidence.py themes --file <evidence.yaml> [--since YYYY-MM-DD]

Exit codes: 0 ok, 1 invalid ledger, 2 unreadable input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml

SOURCES = {"jira", "notion", "slack", "support", "interview", "survey", "analytics", "stakeholder", "sales", "other"}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{8,}\d(?!\w)")
REQUIRED = ("id", "date", "source", "ref", "who", "quote")


def load(path: str) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("the ledger must be a mapping with goals, themes, and evidence")
    return data


def as_date(value) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def check(data: dict) -> dict:
    errors, warnings = [], []
    goals = data.get("goals") or {}
    themes = data.get("themes") or {}
    evidence = data.get("evidence") or []
    if not isinstance(goals, dict) or not isinstance(themes, dict) or not isinstance(evidence, list):
        return {"ok": False, "errors": ["goals and themes are mappings, evidence is a list"], "warnings": []}
    for tid, t in themes.items():
        goal = (t or {}).get("goal") if isinstance(t, dict) else None
        if not isinstance(t, dict) or not t.get("name"):
            errors.append(f"theme {tid} needs a name")
        if goal and goal not in goals:
            errors.append(f"theme {tid} points to goal {goal}, which isn't in goals")
        if not goal:
            warnings.append(f"theme {tid} has no goal")
    seen = set()
    for i, e in enumerate(evidence):
        where = f"evidence {e.get('id', f'#{i + 1}')}" if isinstance(e, dict) else f"evidence #{i + 1}"
        if not isinstance(e, dict):
            errors.append(f"{where} is not a mapping")
            continue
        for field in REQUIRED:
            if not str(e.get(field, "")).strip():
                errors.append(f"{where} needs {field}")
        if e.get("id") in seen:
            errors.append(f"{where}: id is used twice")
        seen.add(e.get("id"))
        if e.get("date") and not as_date(e["date"]):
            errors.append(f"{where}: date must be YYYY-MM-DD")
        if e.get("source") and e["source"] not in SOURCES:
            errors.append(f"{where}: source '{e['source']}' is not one of {', '.join(sorted(SOURCES))}")
        for field in ("who", "quote"):
            text = str(e.get(field, ""))
            if EMAIL.search(text) or any(sum(c.isdigit() for c in m[0]) >= 9 for m in PHONE.finditer(text)):
                errors.append(f"{where}: {field} contains an email or phone number; anonymize it")
        for t in e.get("themes") or []:
            if t not in themes:
                errors.append(f"{where}: theme {t} isn't in themes")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "evidence": len(evidence),
            "themes": len(themes), "goals": len(goals)}


def strength(people: int, channels: int) -> str:
    if people >= 3 and channels >= 2:
        return "strong"
    return "emerging" if people >= 2 else "anecdote"


def rank(data: dict, since: date | None = None) -> dict:
    themes = data.get("themes") or {}
    rows: dict[str, dict] = {}
    untagged = 0
    for e in data.get("evidence") or []:
        d = as_date(e.get("date"))
        if since and (d is None or d < since):
            continue
        tags = e.get("themes") or []
        if not tags:
            untagged += 1
        for t in tags:
            r = rows.setdefault(t, {"people": set(), "channels": set(), "segments": set(), "mentions": 0, "dates": [], "evidence": []})
            r["people"].add(str(e.get("who", "")).strip().lower())
            r["channels"].add(e.get("source"))
            if e.get("segment"):
                r["segments"].add(str(e["segment"]))
            r["mentions"] += 1
            if d:
                r["dates"].append(d)
            r["evidence"].append(e.get("id"))
    out = []
    for tid, r in rows.items():
        meta = themes.get(tid) or {}
        out.append({"theme": tid, "name": meta.get("name", tid), "goal": meta.get("goal"),
                    "people": len(r["people"]), "channels": sorted(c for c in r["channels"] if c),
                    "mentions": r["mentions"], "segments": sorted(r["segments"]),
                    "first_seen": min(r["dates"]).isoformat() if r["dates"] else None,
                    "last_seen": max(r["dates"]).isoformat() if r["dates"] else None,
                    "strength": strength(len(r["people"]), len(r["channels"])), "evidence": r["evidence"]})
    out.sort(key=lambda x: (x["people"], len(x["channels"]), x["mentions"], x["last_seen"] or ""), reverse=True)
    return {"ok": True, "since": since.isoformat() if since else None, "themes": out, "untagged": untagged}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["check", "themes"])
    p.add_argument("--file", required=True)
    p.add_argument("--since", help="themes: only evidence on or after this date")
    args = p.parse_args(argv)
    try:
        data = load(args.file)
        since = date.fromisoformat(args.since) if args.since else None
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(json.dumps({"ok": False, "error": f"bad input: {exc}"}))
        return 2
    out = check(data) if args.cmd == "check" else rank(data, since)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
