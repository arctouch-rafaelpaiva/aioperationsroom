#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""aor-agent-qa: trace acceptance criteria to scenarios and results, and compute a release verdict.

Scenario files follow references/scenario-format.md: frontmatter (story, ac = the
story's AC count), then `## Scenario: <title>` blocks with `covers:`, `kind:`,
`test:`, `status:`, and `evidence:` lines, and an optional `## Challenge` list.

  check    one scenario file: every AC covered, valid kinds and statuses, evidence on
           every pass or fail, and a warning for an AC with only happy-path scenarios.
           Prints the AC matrix (each AC's result: fail > blocked > untested > pass).
  verdict  several scenario files plus an optional defects list, gives go,
           go-with-risks, or no-go with every reason:
             no-go         an AC failed, an AC is uncovered, or an open defect has a
                           blocking severity (--block, default critical,high)
             go-with-risks an AC is untested or blocked, or an open defect of
                           another severity is not low
             go            everything else; open low defects are listed as notes

--defects FILE is JSON: [{"key", "summary", "severity", "open": true|false, "story"?}].

Usage:
  uv run qa_matrix.py check --file <scenarios.md>
  uv run qa_matrix.py verdict --file <a.md> --file <b.md> [--defects <defects.json>] [--block critical,high] [--format json|md]

Exit codes: 0 ok (any verdict), 1 invalid scenario file, 2 unreadable input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

KINDS = {"happy", "negative", "boundary", "state", "permission", "data", "a11y", "regression"}
STATUSES = {"untested", "pass", "fail", "blocked"}
RANK = {"fail": 3, "blocked": 2, "untested": 1, "pass": 0}
FIELDS = ("covers", "kind", "test", "status", "evidence")


def parse(text: str) -> dict:
    meta: dict[str, str] = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if m:
        for line in m[1].splitlines():
            line = line.split(" #", 1)[0].rstrip()
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip().strip("'\"")
        text = text[m.end():]
    scenarios, challenges, current, in_challenge = [], [], None, False
    for line in text.splitlines():
        if h := re.match(r"^##\s+Scenario:\s*(.+)$", line):
            current = {"title": h[1].strip(), "steps": []}
            scenarios.append(current)
            in_challenge = False
        elif re.match(r"^##\s+Challenge\s*$", line, re.I):
            current, in_challenge = None, True
        elif in_challenge and (i := re.match(r"^\s*[-*]\s+(.*)$", line)):
            challenges.append(i[1].strip())
        elif current is not None and (f := re.match(rf"^({'|'.join(FIELDS)}):\s*(.*?)\s*$", line, re.I)):
            current[f[1].lower()] = f[2].split(" #", 1)[0].strip()
        elif current is not None and line.strip():
            current["steps"].append(line.strip())
    return {"meta": meta, "scenarios": scenarios, "challenges": challenges}


def check(doc: dict, source: str = "") -> dict:
    meta, errors, warnings = doc["meta"], [], []
    story = meta.get("story", "")
    if not story:
        errors.append("frontmatter needs story: the story key or slug")
    try:
        ac_count = int(meta.get("ac", ""))
        if ac_count < 1:
            raise ValueError
    except ValueError:
        ac_count = 0
        errors.append("frontmatter needs ac: the number of acceptance criteria in the story (1 or more)")
    if not doc["scenarios"]:
        errors.append("no scenarios: add '## Scenario: <title>' blocks")
    titles = [s["title"].lower() for s in doc["scenarios"]]
    for dup in sorted({t for t in titles if titles.count(t) > 1}):
        errors.append(f"two scenarios share the title '{dup}'")
    matrix = {f"AC{i}": {"scenarios": [], "kinds": set(), "result": "uncovered"} for i in range(1, ac_count + 1)}
    for s in doc["scenarios"]:
        where = f"scenario '{s['title']}'"
        refs = re.findall(r"\bAC\s*(\d+)\b", s.get("covers", ""), re.I)
        if not refs:
            errors.append(f"{where}: needs covers: AC1, AC2 …")
        kind = s.get("kind", "").lower()
        if kind not in KINDS:
            errors.append(f"{where}: kind '{kind}' is not one of {', '.join(sorted(KINDS))}")
        status = s.get("status", "untested").lower()
        if status not in STATUSES:
            errors.append(f"{where}: status '{status}' is not one of {', '.join(sorted(STATUSES))}")
            status = "untested"
        if status in ("pass", "fail") and not s.get("evidence"):
            errors.append(f"{where}: a {status} needs evidence: a link to the run, recording, or report")
        if not s.get("test"):
            warnings.append(f"{where}: no test: line (an automated test id, manual, or none)")
        s["status"] = status
        for n in refs:
            key = f"AC{int(n)}"
            if key not in matrix:
                errors.append(f"{where}: covers {key}, but the story has {ac_count} AC")
                continue
            cell = matrix[key]
            cell["scenarios"].append(s["title"])
            cell["kinds"].add(kind)
            cell["result"] = status if cell["result"] == "uncovered" or RANK[status] > RANK[cell["result"]] else cell["result"]
    for key, cell in matrix.items():
        if cell["result"] == "uncovered":
            errors.append(f"{key} has no scenario")
        elif cell["kinds"] <= {"happy"}:
            warnings.append(f"{key} only has happy-path scenarios; add one that tries to break it")
    out_matrix = {k: {"scenarios": v["scenarios"], "kinds": sorted(v["kinds"]), "result": v["result"]} for k, v in matrix.items()}
    return {"ok": not errors, "file": source, "story": story, "errors": errors, "warnings": warnings,
            "matrix": out_matrix, "challenges": doc["challenges"]}


def verdict(checks: list[dict], defects: list[dict], block: set[str]) -> dict:
    no_go, risks, notes, stories = [], [], [], []
    for c in checks:
        counts = {r: 0 for r in ("pass", "fail", "blocked", "untested", "uncovered")}
        for key, cell in c["matrix"].items():
            counts[cell["result"]] += 1
            label = f"{c['story']} {key}"
            if cell["result"] in ("fail", "uncovered"):
                no_go.append(f"{label} {'failed' if cell['result'] == 'fail' else 'has no scenario'}")
            elif cell["result"] in ("blocked", "untested"):
                risks.append(f"{label} is {cell['result']}")
        for problem in c["errors"]:
            if not re.match(r"^AC\d+ has no scenario$", problem):
                no_go.append(f"{c['story'] or c['file']}: {problem}")
        stories.append({"story": c["story"], "ac": len(c["matrix"]), **counts})
    for d in defects:
        if not d.get("open", True):
            continue
        sev = str(d.get("severity", "")).lower()
        line = f"{d.get('key', '?')} ({sev or 'no severity'}) open: {d.get('summary', '')}".rstrip(": ")
        if sev in block:
            no_go.append(line)
        elif sev == "low":
            notes.append(line)
        else:
            risks.append(line)
    result = "no-go" if no_go else "go-with-risks" if risks else "go"
    return {"ok": True, "verdict": result, "no_go": no_go, "risks": risks, "notes": notes, "stories": stories,
            "blocking_severities": sorted(block)}


def render(v: dict) -> str:
    out = [f"**Verdict: {v['verdict']}**", "", "| Story | AC | Pass | Fail | Blocked | Untested | Uncovered |", "|---|---|---|---|---|---|---|"]
    out += [f"| {s['story']} | {s['ac']} | {s['pass']} | {s['fail']} | {s['blocked']} | {s['untested']} | {s['uncovered']} |" for s in v["stories"]]
    for title, key in (("Blocking", "no_go"), ("Risks", "risks"), ("Notes", "notes")):
        if v[key]:
            out += ["", f"**{title}**", *[f"- {x}" for x in v[key]]]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["check", "verdict"])
    p.add_argument("--file", action="append", required=True, help="scenario file; repeat for verdict")
    p.add_argument("--defects", help="verdict: JSON list of defects")
    p.add_argument("--block", default="critical,high", help="verdict: severities that block a release")
    p.add_argument("--format", choices=["json", "md"], default="json")
    args = p.parse_args(argv)
    try:
        checks = [check(parse(Path(f).read_text(encoding="utf-8")), f) for f in args.file]
        defects = json.loads(Path(args.defects).read_text(encoding="utf-8")) if args.defects else []
        if not isinstance(defects, list):
            raise ValueError("defects must be a JSON list")
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": f"bad input: {exc}"}))
        return 2
    if args.cmd == "check":
        if len(checks) != 1:
            print(json.dumps({"ok": False, "error": "check takes one --file"}))
            return 2
        print(json.dumps(checks[0], ensure_ascii=False, indent=2))
        return 0 if checks[0]["ok"] else 1
    v = verdict(checks, defects, {s.strip().lower() for s in args.block.split(",") if s.strip()})
    print(render(v) if args.format == "md" else json.dumps(v, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
