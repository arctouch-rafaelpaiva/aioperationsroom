#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""
Seed one squad member's sanctum inside one project.

A squad member's memory belongs to its project: {root}/_bmad/memory/aor/projects/
<project>/squad/<member>/. This writes INDEX, PERSONA, CREED, BOND, and MEMORY from
assets/*-template.md, plus sessions/. The name and persona overrides come from the
member's roster entry in project.yaml; without a roster name the role's default
name is used. Capabilities are not copied: wake.py lists them from the skill's
references, so every project always sees the current set.

Paths written into the sanctum stay `{project-root}`-relative, so the files are
valid in every clone of the ops repo.

It reads config.yaml / config.user.yaml only to substitute user_name and
communication_language. It never writes config or customize.toml.

Usage:
    uv run init-sanctum.py <project-root> <skill-path> --project <id> [--member <id>]

Output: JSON {ok, created, sanctum, member, name}. Exit codes: 0 created or
already present (created: false), 1 invalid (unknown project or member).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROLE = "discovery"
DEFAULT_MEMBER = f"aor-agent-{ROLE}"
DEFAULT_NAME = "Noor"
DEFAULT_ICON = "🧭"
TEMPLATE_FILES = ["INDEX", "PERSONA", "CREED", "BOND", "MEMORY"]
PROJECTS = Path("_bmad/memory/aor/projects")


class Invalid(Exception):
    pass


def read_flat(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*?)\s*$", line)
            if m and m[2]:
                out[m[1]] = m[2].strip("'\"")
    return out


def roster_entry(root: Path, project: str, member: str) -> dict:
    yaml_path = root / PROJECTS / project / "project.yaml"
    if not yaml_path.is_file():
        known = sorted(p.parent.name for p in (root / PROJECTS).glob("*/project.yaml"))
        raise Invalid(f"project '{project}' not found; known projects: {known or 'none'}")
    import yaml

    proj = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    roster = [e for e in proj.get("roster") or [] if isinstance(e, dict)]
    for entry in roster:
        if entry.get("id") == member:
            if entry.get("skill", DEFAULT_MEMBER) != DEFAULT_MEMBER:
                raise Invalid(f"{member} on {project} runs {entry.get('skill')}, not {DEFAULT_MEMBER}")
            return entry
    if member == DEFAULT_MEMBER:
        return {"id": member, "role": ROLE, "skill": DEFAULT_MEMBER, "off_roster": True}
    ids = [e.get("id") for e in roster]
    raise Invalid(f"{member} is not on {project}'s roster: {ids}")


def sanctum_dir(root: Path, project: str, member: str) -> Path:
    return root / PROJECTS / project / "squad" / member


def seed(root: Path, skill: Path, project: str, member: str) -> dict:
    entry = roster_entry(root, project, member)
    sanctum = sanctum_dir(root, project, member)
    name = entry.get("name") or DEFAULT_NAME
    if (sanctum / "CREED.md").is_file():
        return {"ok": True, "created": False, "sanctum": str(sanctum), "member": member, "name": name}
    cfg: dict[str, str] = {}
    for f in ("config.yaml", "config.user.yaml"):
        cfg.update(read_flat(root / "_bmad" / f))
    rel = f"{{project-root}}/{(PROJECTS / project / 'squad' / member).as_posix()}"
    variables = {
        "user_name": cfg.get("user_name", "friend"),
        "communication_language": cfg.get("communication_language", "English"),
        "birth_date": date.today().isoformat(),
        "project_root": "{project-root}",
        "sanctum_path": rel,
    }
    sanctum.mkdir(parents=True, exist_ok=True)
    (sanctum / "sessions").mkdir(exist_ok=True)
    for stem in TEMPLATE_FILES:
        text = (skill / "assets" / f"{stem}-template.md").read_text(encoding="utf-8")
        for key, value in variables.items():
            text = text.replace(f"{{{key}}}", value)
        if stem == "PERSONA":
            text = text.replace("- **Name:** {awaiting First Breath}", f"- **Name:** {name}")
            text = text.replace("- **Icon:** {awaiting First Breath}", f"- **Icon:** {DEFAULT_ICON}")
            text = text.replace("- **Title:**", f"- **Project:** {project}\n- **Member id:** {member}\n- **Title:**", 1)
            if entry.get("persona"):
                text += f"\n## Roster Persona\n{entry['persona']}\n"
        (sanctum / f"{stem}.md").write_text(text, encoding="utf-8")
    return {"ok": True, "created": True, "sanctum": str(sanctum), "member": member, "name": name,
            "off_roster": bool(entry.get("off_roster"))}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project_root")
    p.add_argument("skill_path")
    p.add_argument("--project", required=True)
    p.add_argument("--member", default=DEFAULT_MEMBER)
    args = p.parse_args(argv)
    try:
        out = seed(Path(args.project_root).resolve(), Path(args.skill_path).resolve(), args.project, args.member)
    except Invalid as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
