#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""
Waking — load the agent's sanctum in one pass, or route to First Breath.

Run on activation. Determines the mode from the filesystem (and the --pulse
flag) and, when the sanctum exists, prints the full identity in a single read
(INDEX, PERSONA, CREED, BOND, MEMORY, CAPABILITIES) so the agent becomes itself
in one shot instead of six. In --pulse mode it also appends PULSE.md.

aor-agent-maestro additions:
- --pulse with no sanctum scaffolds the seeded sanctum (scheduled runs cannot hold
  First Breath) and reports CALIBRATION: pending until First Breath has happened.
- --task <name> is echoed. Only the `brief` run is the sanctum curator
  (SANCTUM CURATOR: yes); `relay` runs every 30 minutes and never curates.
- Every wake appends the portfolio pre-pass (portfolio.py --format md), so Maestro
  sees every active project's stand-up, wrap, inbox, and silence in the same read.

This loads runtime memory only. It never reads or writes config or customize.toml.

Usage:
    uv run wake.py <project-root> [--pulse] [--task brief|relay]
"""

import subprocess
import sys
from pathlib import Path

SKILL_NAME = "aor-agent-maestro"
UNBORN_MARK = "{Discovered during First Breath."
CURATOR_TASKS = {"brief"}

IDENTITY_FILES = [
    "INDEX.md",
    "PERSONA.md",
    "CREED.md",
    "BOND.md",
    "MEMORY.md",
    "CAPABILITIES.md",
]


def emit(path: Path) -> None:
    print(f"\n===== {path.name} =====")
    try:
        print(path.read_text(encoding="utf-8").rstrip())
    except FileNotFoundError:
        print(f"(missing: {path.name})")


def option(args: list[str], name: str) -> str | None:
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return args[i + 1]
    return None


def main() -> int:
    args = sys.argv[1:]
    pulse = "--pulse" in args
    task = option(args, "--task")
    positional = [a for a in args if not a.startswith("--") and a != task]
    if not positional:
        print("Usage: wake.py <project-root> [--pulse] [--task brief|relay]", file=sys.stderr)
        return 2

    project_root = Path(positional[0]).resolve()
    sanctum = project_root / "_bmad" / "memory" / SKILL_NAME
    here = Path(__file__).resolve().parent

    def core_ok() -> bool:
        return sanctum.is_dir() and (sanctum / "CREED.md").is_file() and (sanctum / "MEMORY.md").is_file()

    if not core_ok() and pulse and (here / "init-sanctum.py").is_file():
        res = subprocess.run([sys.executable, str(here / "init-sanctum.py"), str(project_root), str(here.parent)],
                             capture_output=True, text=True)
        print(f"AUTO-INIT: seeded sanctum for a scheduled run (exit {res.returncode})")

    if not core_ok():
        print("MODE: FIRST_BREATH")
        print(f"NO SANCTUM at {sanctum}")
        print("This is your one birth. Load references/first-breath.md and follow it.")
        return 0

    creed = sanctum / "CREED.md"
    unborn = creed.is_file() and UNBORN_MARK in creed.read_text(encoding="utf-8")
    if unborn and not pulse:
        print("MODE: FIRST_BREATH")
        print(f"SEEDED SANCTUM at {sanctum} (a scheduled run started it; init will skip).")
        print("This is your one birth. Load references/first-breath.md and follow it.")
    else:
        print("MODE: PULSE" if pulse else "MODE: WAKING")
    print(f"Sanctum: {sanctum}")
    if pulse:
        print(f"CALIBRATION: {'pending' if unborn else 'done'}")
        if task:
            print(f"TASK: {task}")
        print(f"SANCTUM CURATOR: {'yes' if task in CURATOR_TASKS else 'no'}")
    for name in IDENTITY_FILES:
        emit(sanctum / name)
    if pulse:
        emit(sanctum / "PULSE.md")

    sys.path.insert(0, str(here))
    import portfolio  # noqa: E402

    try:
        snapshot = portfolio.portfolio(project_root, portfolio.datetime.now(portfolio.timezone.utc), 26)
    except Exception as exc:  # the pre-pass must never block waking
        print(f"\n===== PORTFOLIO =====\nPORTFOLIO UNAVAILABLE: {type(exc).__name__}: {exc}")
        return 0
    print()
    print(portfolio.render(snapshot))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
