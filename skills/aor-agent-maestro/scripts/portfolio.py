#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""aor-agent-maestro: the portfolio pre-pass for the brief and relay runs.

For every active project in {root}/_bmad/memory/aor/projects/: today's stand-up
(text, or missing), the latest wrap, open and untriaged inbox counts, and the last
PM-side activity from the daily logs. Flags projects with no stand-up by brief time
and projects silent for longer than --silent-hours (a PM run likely failed). Also
lists Maestro's unsorted intake (`unsorted/<date>/<run>.md` in its sanctum) since
the last brief.

Room state (fires, asks, approvals) is not read here; get it from aor-signal.

Usage:
  uv run portfolio.py --root <ops repo> [--now ISO] [--silent-hours 26] [--format json|md]

Output: JSON (default) or markdown. Exit codes: 0 ok, 2 error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECTS = Path("_bmad/memory/aor/projects")
SANCTUM = Path("_bmad/memory/aor-agent-maestro")


def aor_config(root: Path) -> dict[str, str]:
    """aor_* keys from the aor section of _bmad/config.yaml (legacy _bmad/aor/config.yaml as fallback)."""
    out: dict[str, str] = {}
    for path in (root / "_bmad" / "aor" / "config.yaml", root / "_bmad" / "config.yaml"):
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                m = re.match(r"^\s*(aor_\w+)\s*:\s*(.*?)\s*(#.*)?$", line)
                if m and m[2]:
                    out[m[1]] = m[2].strip().strip("'\"")
    return out


def local_tz(root: Path):
    name = aor_config(root).get("aor_timezone", "America/Sao_Paulo")
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:
        return timezone.utc


def last_activity(base: Path, tz) -> datetime | None:
    days = sorted((d for d in (base / "daily").glob("*") if d.is_dir()), key=lambda d: d.name)
    for day in reversed(days):
        times = []
        for f in day.glob("*.md"):
            times += re.findall(r"^- (\d{2}):(\d{2}) \[", f.read_text(encoding="utf-8"), re.M)
        if times:
            h, m = max((int(a), int(b)) for a, b in times)
            try:
                d = datetime.fromisoformat(day.name)
            except ValueError:
                continue
            return d.replace(hour=h, minute=m, tzinfo=tz)
    return None


def portfolio(root: Path, now: datetime, silent_hours: float) -> dict:
    tz = local_tz(root)
    local = now.astimezone(tz)
    today = local.date().isoformat()
    projects, missing, silent = [], [], []
    for yaml in sorted((root / PROJECTS).glob("*/project.yaml")):
        text = yaml.read_text(encoding="utf-8")
        if not re.search(r"^status:\s*active\s*$", text, re.M):
            continue
        base, pid = yaml.parent, yaml.parent.name
        name = (re.search(r"^name:\s*(.+)$", text, re.M) or [None, pid])[1].strip().strip("'\"")
        standup = base / "standup" / f"{today}.md"
        eods = sorted((base / "eod").glob("*.md"))
        inbox = [f.read_text(encoding="utf-8") for f in sorted((base / "inbox").glob("*.md"))]
        statuses = [(re.search(r"^status:\s*(\w+)", t, re.M) or [None, "new"])[1] for t in inbox]
        act = last_activity(base, tz)
        entry = {
            "id": pid,
            "name": name,
            "standup_today": standup.read_text(encoding="utf-8").strip() if standup.is_file() else None,
            "latest_eod": eods[-1].stem if eods else None,
            "inbox_open": sum(s in ("new", "routed") for s in statuses),
            "inbox_untriaged": statuses.count("new"),
            "last_activity": act.isoformat() if act else None,
        }
        projects.append(entry)
        if entry["standup_today"] is None:
            missing.append(pid)
        if act is None or local - act > timedelta(hours=silent_hours):
            silent.append(pid)
    last_brief = sorted((root / SANCTUM / "briefs").glob("*.md"))
    since = last_brief[-1].stem if last_brief else ""
    unsorted = []
    for day in sorted(d for d in (root / SANCTUM / "unsorted").glob("*") if d.is_dir() and d.name >= since):
        for f in sorted(day.glob("*.md")):
            unsorted += [line for line in f.read_text(encoding="utf-8").splitlines() if line.startswith("- ")]
    return {"ok": True, "today": today, "weekday": local.strftime("%A"), "projects": projects,
            "missing_standups": missing, "silent_projects": silent, "unsorted": unsorted}


def render(p: dict) -> str:
    out = [f"===== PORTFOLIO {p['today']} ({p['weekday']}) ====="]
    if p["missing_standups"]:
        out.append(f"MISSING STAND-UPS: {', '.join(p['missing_standups'])}")
    if p["silent_projects"]:
        out.append(f"SILENT PROJECTS: {', '.join(p['silent_projects'])}")
    for proj in p["projects"]:
        out += ["", f"--- {proj['id']} ({proj['name']}): inbox {proj['inbox_open']} open / {proj['inbox_untriaged']} untriaged; "
                    f"last wrap {proj['latest_eod'] or 'none'}; last activity {proj['last_activity'] or 'none'} ---",
                proj["standup_today"] or "(no stand-up today)"]
    if p["unsorted"]:
        out += ["", "--- unsorted intake since the last brief ---", *p["unsorted"]]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--now")
    ap.add_argument("--silent-hours", type=float, default=26)
    ap.add_argument("--format", choices=["json", "md"], default="json")
    args = ap.parse_args(argv)
    try:
        now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
        p = portfolio(Path(args.root).resolve(), now, args.silent_hours)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        return 2
    print(render(p) if args.format == "md" else json.dumps(p, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
