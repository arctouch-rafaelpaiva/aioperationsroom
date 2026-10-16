#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""aor-setup: prepare the ops repo for the AI Operations Room after config is written.

Idempotent. It:
  - checks the root is a git work tree with a remote (scheduled runs clone it);
  - creates _bmad/memory/aor/projects/ and aor/room/ (with .gitkeep files);
  - makes sure .gitignore ignores _bmad/config.user.yaml (personal settings);
  - writes _bmad/memory/aor/automations.md, the room-level Cursor automations
    (Maestro's brief and relay), from the aor section of _bmad/config.yaml.
    Per-project automations come from aor-onboard-project.

Usage:
  uv run room_setup.py --root <ops repo> [--dry-run]

Output is JSON: {"ok", "git", "created", "gitignore", "checklist", "warnings"}.
Exit codes: 0 ok (warnings allowed), 2 the root is not a directory.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DEFAULTS = {
    "aor_timezone": "America/Sao_Paulo",
    "aor_brief_time": "08:30",
    "aor_slack_batch_minutes": "30",
    "aor_ops_repo": "aor-ops",
}
DIRS = ["_bmad/memory/aor/projects", "aor/room"]
IGNORE = "_bmad/config.user.yaml"
CHECKLIST = Path("_bmad/memory/aor/automations.md")


def aor_config(root: Path) -> dict[str, str]:
    """aor_* keys from the aor section of _bmad/config.yaml (legacy _bmad/aor/config.yaml as fallback)."""
    out: dict[str, str] = dict(DEFAULTS)
    for path in (root / "_bmad" / "aor" / "config.yaml", root / "_bmad" / "config.yaml"):
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                m = re.match(r"^\s*(aor_\w+)\s*:\s*(.*?)\s*(#.*)?$", line)
                if m and m[2]:
                    out[m[1]] = m[2].strip().strip("'\"")
    return out


def utc_cron_weekdays(hhmm: str, tz: str, now: datetime) -> str | None:
    m = re.fullmatch(r"(\d{2}):(\d{2})", hhmm)
    if not m:
        return None
    try:
        from zoneinfo import ZoneInfo

        local = now.astimezone(ZoneInfo(tz)).replace(hour=int(m[1]), minute=int(m[2]), second=0, microsecond=0)
    except Exception:
        return None
    utc = local.astimezone(ZoneInfo("UTC"))
    if utc.date() != local.date():
        return None
    return f"{utc.minute} {utc.hour} * * 1-5"


def checklist(cfg: dict[str, str], now: datetime) -> str:
    tz, brief = cfg["aor_timezone"], cfg["aor_brief_time"]
    cron = utc_cron_weekdays(brief, tz, now)
    minutes = cfg["aor_slack_batch_minutes"]
    every = int(minutes) if minutes.isdigit() and int(minutes) > 0 else 30
    relay_cron = f"*/{every} * * * *" if every < 60 and 60 % every == 0 else None
    run = "Use this run's id as AOR_RUN_ID."
    rows = [
        ("aor Maestro morning brief", f"Mon–Fri {brief} {tz}" + (f" (UTC cron `{cron}`)" if cron else ""),
         f"Run aor-agent-maestro --pulse --task brief. {run}"),
        ("aor Maestro relay", f"Every {every} minutes, every day" + (f" (cron `{relay_cron}`)" if relay_cron else ""),
         f"Run aor-agent-maestro --pulse --task relay. {run}"),
    ]
    return "\n".join([
        "# Room automations",
        "",
        f"Create each in the Cursor dashboard (Cloud Agents → Automations) on the `{cfg['aor_ops_repo']}` repo, default branch.",
        "Each project adds its own (stand-up, wrap, events, polls) in its `automations.md`, written by aor-onboard-project.",
        "Regenerate this file by running aor-setup again after changing the brief time, timezone, or batch minutes.",
        "",
        "| Automation | Trigger | Prompt |",
        "|---|---|---|",
        *[f"| {a} | {t} | {p} |" for a, t, p in rows],
        "",
        "Secrets these runs use (Cloud Agents → Secrets): `AOR_SLACK_BOT_TOKEN` (Maestro posts as the room bot; without it,",
        "posts go through the Slack MCP as you, with no notification). Later, with the room app: `AOR_ROOM_URL`, `AOR_ROOM_TOKEN`.",
    ]) + "\n"


def git_state(root: Path) -> dict:
    def run(*args):
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)

    inside = run("rev-parse", "--is-inside-work-tree").stdout.strip() == "true"
    remotes = run("remote").stdout.split() if inside else []
    return {"repo": inside, "remote": bool(remotes)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(json.dumps({"ok": False, "error": f"{root} is not a directory"}))
        return 2
    warnings, created = [], []
    git = git_state(root)
    if not git["repo"]:
        warnings.append("not a git repo: scheduled runs clone the ops repo, so initialize it and push it to a private remote")
    elif not git["remote"]:
        warnings.append("no git remote: push the ops repo to a private remote so automations can clone it")

    for d in DIRS:
        path = root / d
        if not path.is_dir():
            created.append(d)
            if not args.dry_run:
                path.mkdir(parents=True, exist_ok=True)
                (path / ".gitkeep").touch()

    gi = root / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.is_file() else []
    gitignore = "already ignored" if IGNORE in (line.strip() for line in lines) else "added"
    if gitignore == "added" and not args.dry_run:
        gi.write_text("\n".join([*lines, IGNORE]).lstrip("\n") + "\n", encoding="utf-8")

    cfg = aor_config(root)
    if not (root / "_bmad" / "config.yaml").is_file():
        warnings.append("_bmad/config.yaml not found: run the config step first; the checklist uses defaults")
    text = checklist(cfg, datetime.now().astimezone())
    if not args.dry_run:
        (root / CHECKLIST).parent.mkdir(parents=True, exist_ok=True)
        (root / CHECKLIST).write_text(text, encoding="utf-8")
    print(json.dumps({"ok": True, "dry_run": args.dry_run, "git": git, "created": created, "gitignore": gitignore,
                      "checklist": CHECKLIST.as_posix(), "checklist_text": text, "warnings": warnings},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
