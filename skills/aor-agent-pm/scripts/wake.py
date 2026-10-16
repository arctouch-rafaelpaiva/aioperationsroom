#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""
Waking — load this project's PM in one pass, or route to First Breath.

One PM per squad: the PM's sanctum belongs to its project, at {root}/_bmad/memory/
aor/projects/<project>/squad/aor-agent-pm/. Wake prints, in a single read: the mode,
the sanctum (INDEX, PERSONA, CREED, BOND, MEMORY, and PULSE when --pulse), the
capabilities listed from this skill's references, and the project's working set.

- No --project: lists the active projects (MODE: NEED_PROJECT).
- --pulse with no sanctum seeds one (scheduled runs cannot hold First Breath) and
  reports CALIBRATION: pending until this project's First Breath has happened.
- --task is echoed; `eod` is this project's sanctum curator (SANCTUM CURATOR: yes),
  so concurrent stand-up and triage runs never edit the core sanctum files.

This loads runtime memory only. It never reads or writes config or customize.toml.

Usage:
    uv run wake.py <project-root> [--project <id>] [--pulse] [--task standup|triage|eod]
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
UNBORN_MARK = "{Discovered during First Breath."
CURATOR_TASKS = {"eod"}
IDENTITY_FILES = ["INDEX.md", "PERSONA.md", "CREED.md", "BOND.md", "MEMORY.md"]


def load_init():
    spec = importlib.util.spec_from_file_location("init_sanctum", HERE / "init-sanctum.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def emit(path: Path) -> None:
    print(f"\n===== {path.name} =====")
    try:
        print(path.read_text(encoding="utf-8").rstrip())
    except FileNotFoundError:
        print(f"(missing: {path.name})")


def capabilities() -> str:
    rows = []
    for md in sorted((SKILL / "references").glob("*.md")):
        m = re.match(r"^---\s*\n(.*?)\n---", md.read_text(encoding="utf-8"), re.S)
        meta = dict(re.findall(r"^(\w+):\s*(.*?)\s*$", m[1], re.M)) if m else {}
        if meta.get("code") and meta.get("name"):
            rows.append(f"| [{meta['code']}] | {meta['name']} | {meta.get('description', '')} | `references/{md.name}` |")
    return "\n".join(["| Code | Name | Description | Source |", "|---|---|---|---|", *rows])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project_root")
    p.add_argument("--project")
    p.add_argument("--pulse", action="store_true")
    p.add_argument("--task")
    args = p.parse_args(argv)
    root = Path(args.project_root).resolve()
    init = load_init()
    sys.path.insert(0, str(HERE))
    import project_memory  # noqa: E402

    if not args.project:
        active = project_memory.active_projects(root)
        print("MODE: NEED_PROJECT")
        print(f"Active projects: {', '.join(active) or 'none'}")
        print("Ask which project, then wake again with --project <id>.")
        return 0

    try:
        init.roster_entry(root, args.project, init.DEFAULT_MEMBER)
    except init.Invalid as exc:
        print(f"MODE: {'PULSE' if args.pulse else 'WAKING'}\nPROJECT NOT FOUND: {exc}")
        return 0

    sanctum = init.sanctum_dir(root, args.project, init.DEFAULT_MEMBER)
    if not (sanctum / "CREED.md").is_file() and args.pulse:
        res = init.seed(root, SKILL, args.project, init.DEFAULT_MEMBER)
        print(f"AUTO-INIT: seeded the PM on {args.project} for a scheduled run ({res['name']})")

    if not (sanctum / "CREED.md").is_file():
        print("MODE: FIRST_BREATH")
        print(f"NO SANCTUM for the PM on {args.project}.")
        print(f"Run init-sanctum.py with --project {args.project}, then load references/first-breath.md.")
        return 0

    unborn = UNBORN_MARK in (sanctum / "CREED.md").read_text(encoding="utf-8")
    if unborn and not args.pulse:
        print("MODE: FIRST_BREATH")
        print(f"SEEDED SANCTUM for the PM on {args.project} (a scheduled run started it; init will skip).")
        print("Load references/first-breath.md and follow it.")
    else:
        print("MODE: PULSE" if args.pulse else "MODE: WAKING")
    print(f"Project: {args.project}\nSanctum: {sanctum}")
    if args.pulse:
        print(f"CALIBRATION: {'pending' if unborn else 'done'}")
        if args.task:
            print(f"TASK: {args.task}")
        print(f"SANCTUM CURATOR: {'yes' if args.task in CURATOR_TASKS else 'no'}")
    for name in IDENTITY_FILES:
        emit(sanctum / name)
    if args.pulse:
        emit(sanctum / "PULSE.md")
    print("\n===== CAPABILITIES =====")
    print(capabilities())

    try:
        ctx = project_memory.context(root, args.project, datetime.now(timezone.utc))
    except project_memory.Invalid as exc:
        print(f"\n===== PROJECT {args.project} =====\nPROJECT NOT FOUND: {exc}")
        return 0
    print(project_memory.render_context(ctx))
    return 0


if __name__ == "__main__":
    sys.exit(main())
