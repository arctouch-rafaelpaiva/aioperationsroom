#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""
Waking — load this project's copy of the squad member in one pass, or route to First Breath.

A squad member has one sanctum per project, at {root}/_bmad/memory/aor/projects/
<project>/squad/<member>/. Wake prints, in a single read: the mode, the sanctum
(INDEX, PERSONA, CREED, BOND, MEMORY), the capabilities listed from this skill's
references, and the project's working set (aor-agent-pm's project_memory.py).

- No --project: lists the projects whose roster runs this skill (MODE: NEED_PROJECT).
- --headless with no sanctum seeds one (the PM's cue can't hold First Breath) and
  reports CALIBRATION: pending until this project's First Breath has happened.
- --task is echoed (e.g. a capability code, or curate).

This loads runtime memory only. It never reads or writes config or customize.toml.

Usage:
    uv run wake.py <project-root> [--project <id>] [--member <id>] [--headless] [--task <code>]
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


def project_memory_module():
    candidate = SKILL.parent / "aor-agent-pm" / "scripts"
    if not (candidate / "project_memory.py").is_file():
        return None
    sys.path.insert(0, str(candidate))
    import project_memory  # noqa: E402

    return project_memory


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project_root")
    p.add_argument("--project")
    p.add_argument("--member")
    p.add_argument("--headless", action="store_true")
    p.add_argument("--task")
    args = p.parse_args(argv)
    root = Path(args.project_root).resolve()
    init = load_init()
    member = args.member or init.DEFAULT_MEMBER

    if not args.project:
        mine = []
        for y in sorted((root / init.PROJECTS).glob("*/project.yaml")):
            text = y.read_text(encoding="utf-8")
            if re.search(r"^status:\s*active\s*$", text, re.M) and f"skill: {init.DEFAULT_MEMBER}" in text:
                mine.append(y.parent.name)
        print("MODE: NEED_PROJECT")
        print(f"Projects whose squad runs {init.DEFAULT_MEMBER}: {', '.join(mine) or 'none'}")
        print("Ask which project, then wake again with --project <id>.")
        return 0

    try:
        init.roster_entry(root, args.project, member)
    except init.Invalid as exc:
        print(f"MODE: INVALID\nPROJECT OR MEMBER NOT FOUND: {exc}")
        return 0

    sanctum = init.sanctum_dir(root, args.project, member)
    if not (sanctum / "CREED.md").is_file() and args.headless:
        res = init.seed(root, SKILL, args.project, member)
        print(f"AUTO-INIT: seeded {member} on {args.project} for a headless cue ({res['name']})")

    if not (sanctum / "CREED.md").is_file():
        print("MODE: FIRST_BREATH")
        print(f"NO SANCTUM for {member} on {args.project}.")
        print(f"Run init-sanctum.py with --project {args.project} --member {member}, then load references/first-breath.md.")
        return 0

    unborn = UNBORN_MARK in (sanctum / "CREED.md").read_text(encoding="utf-8")
    if unborn and not args.headless:
        print("MODE: FIRST_BREATH")
        print(f"SEEDED SANCTUM for {member} on {args.project} (a headless cue started it; init will skip).")
        print("Load references/first-breath.md and follow it.")
    else:
        print("MODE: HEADLESS" if args.headless else "MODE: WAKING")
    print(f"Project: {args.project}\nMember: {member}\nSanctum: {sanctum}")
    if args.headless:
        print(f"CALIBRATION: {'pending' if unborn else 'done'}")
        if args.task:
            print(f"TASK: {args.task}")
    for name in IDENTITY_FILES:
        emit(sanctum / name)
    print("\n===== CAPABILITIES =====")
    print(capabilities())

    pm = project_memory_module()
    if pm is None:
        print("\n===== PROJECT =====\n(aor-agent-pm's project_memory.py not found; read project memory directly)")
        return 0
    try:
        ctx = pm.context(root, args.project, datetime.now(timezone.utc))
    except pm.Invalid as exc:
        print(f"\n===== PROJECT =====\nPROJECT NOT FOUND: {exc}")
        return 0
    print(pm.render_context(ctx))
    return 0


if __name__ == "__main__":
    sys.exit(main())
