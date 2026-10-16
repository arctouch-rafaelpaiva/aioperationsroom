#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""aor-onboard-project: the registry of AI Operations Room projects.

Owns {root}/_bmad/memory/aor/projects/{id}/project.yaml (schema, defaults,
validation), the project memory scaffold, archiving, and the Cursor automation
checklist. The room draws one pod per active project.yaml, so this file is the
registry; activity still goes through aor-signal.

Mutating commands print `changed` (paths to commit) and `room_signals` (argv lists
for aor-signal's room_signal.py, so characters appear or leave live). The script
never commits and never calls aor-signal itself.

Config: flat `key: value` lines from {root}/_bmad/aor/config.yaml
(aor_timezone, aor_standup_time, aor_eod_time, aor_ops_repo).

Output: JSON on stdout. Exit codes: 0 ok, 1 invalid request (message names the fix),
2 error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

SCHEMA_VERSION = 1
PROJECTS_DIR = Path("_bmad/memory/aor/projects")
SPECIALISTS = ["discovery", "requirements", "docs", "design", "engineering", "qa"]
STANDARD_ROLES = ["pm", *SPECIALISTS]
SPECIALIST_SKILLS = [f"aor-agent-{r}" for r in SPECIALISTS]
TOP_KEYS = {"schema", "id", "name", "status", "created_at", "archived_at", "sources", "roster", "fire", "notes"}
SOURCE_TYPES = ["notion", "jira", "figma", "github", "slack"]
NOTION_KINDS = ["workspace", "teamspace", "page", "database"]
FIGMA_KINDS = ["team", "project", "file"]
SLACK_USES = ["context", "post"]
WORKDAYS_CRON = "1-5"
DEFAULTS = {
    "aor_timezone": "America/Sao_Paulo",
    "aor_standup_time": "08:00",
    "aor_eod_time": "18:00",
    "aor_ops_repo": "aor-ops",
}
HEADER = "# Managed by aor-onboard-project and the room wizard. Validate after any hand edit.\n"
MEMORY_FILES = {
    "index.md": "# {name}\n\nOrientation for everyone on this project; the PM curates it. Sources live in `project.yaml`.\n\n## Recent activity\n",
    "decisions.md": "# Decisions\n\nDated entries, newest last: `- <YYYY-MM-DD> <decision> — <why> (<who>)`.\n",
    "risks.md": "# Risks and blockers\n\nMirror of what was raised through aor-signal `risk open`, with context.\n",
    "open-questions.md": "# Open questions\n\n`- [ ] <question> — owner: <role>, since <YYYY-MM-DD>`.\n",
}
MEMORY_DIRS = ["daily", "inbox", "standup", "eod", "weekly"]


class Invalid(Exception):
    pass


class Rejected(Exception):
    """A complete result that still means exit 1 (validate found errors)."""

    def __init__(self, payload: dict):
        super().__init__("rejected")
        self.payload = payload


# ---------- io ----------

def read_flat_yaml(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*?)\s*(#.*)?$", line)
        if m and m[2]:
            out[m[1]] = m[2].strip().strip("'\"")
    return out


def load_config(root: Path) -> dict[str, str]:
    cfg = dict(DEFAULTS)
    cfg.update({k: v for k, v in read_flat_yaml(root / "_bmad" / "aor" / "config.yaml").items() if k in DEFAULTS})
    return cfg


def normalize_dates(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: normalize_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_dates(v) for v in obj]
    return obj


def project_dir(root: Path, pid: str) -> Path:
    return root / PROJECTS_DIR / pid


def load_project(root: Path, pid: str) -> dict:
    path = project_dir(root, pid) / "project.yaml"
    if not path.is_file():
        known = ", ".join(p.parent.name for p in sorted((root / PROJECTS_DIR).glob("*/project.yaml"))) or "none"
        raise Invalid(f"no project '{pid}' (known: {known}); onboard it first")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise Invalid(f"{path.relative_to(root)} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise Invalid(f"{path.relative_to(root)} must be a YAML mapping")
    return normalize_dates(data)


def save_project(root: Path, proj: dict) -> str:
    path = project_dir(root, proj["id"]) / "project.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(HEADER + yaml.safe_dump(proj, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return rel(root, path)


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def read_spec(path: str) -> dict:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    try:
        spec = json.loads(text)
    except json.JSONDecodeError as exc:
        raise Invalid(f"--spec must be JSON: {exc}") from exc
    if not isinstance(spec, dict):
        raise Invalid("--spec must be a JSON object")
    return spec


# ---------- schema ----------

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40].strip("-")


def roster_entry(role: str, name: str | None = None, based_on: str | None = None, persona: str | None = None) -> dict:
    if role in STANDARD_ROLES:
        entry = {"id": f"aor-agent-{role}", "role": role, "skill": f"aor-agent-{role}"}
    elif role != "custom":
        raise Invalid(f"role '{role}' is unknown; use {', '.join(STANDARD_ROLES)}, or custom")
    else:
        if not name:
            raise Invalid(f"custom agent '{role}' needs --name")
        if based_on not in SPECIALIST_SKILLS:
            raise Invalid(f"custom agent '{name}' needs based_on: one of {', '.join(SPECIALIST_SKILLS)}")
        entry = {"id": f"aor-custom-{slugify(name)}", "role": "custom", "skill": based_on}
    if name:
        entry["name"] = name
    if persona:
        entry["persona"] = persona
    return entry


def output_dir_name(entry: dict) -> str:
    return entry["role"] if entry["role"] != "custom" else entry["id"].removeprefix("aor-custom-")


def check_verified(where: str, item: dict, errors: list, warnings: list) -> None:
    v = item.get("verified", False)
    if v is False:
        warnings.append(f"{where} is unverified; check it when the tool is connected")
    elif not (isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v)):
        errors.append(f"{where}.verified must be a YYYY-MM-DD date or false")


def check_list(name: str, value, errors: list) -> list:
    if not isinstance(value, list) or not value:
        errors.append(f"sources.{name} must be a non-empty list (omit it if unused)")
        return []
    bad = [i for i, x in enumerate(value) if not isinstance(x, dict)]
    if bad:
        errors.append(f"sources.{name}[{bad[0]}] must be a mapping")
    return [x for x in value if isinstance(x, dict)]


def validate_sources(sources, errors: list, warnings: list) -> None:
    if not isinstance(sources, dict) or not sources:
        errors.append(f"sources must map at least one of {', '.join(SOURCE_TYPES)}; the team needs to know where to look")
        return
    for key in sources:
        if key not in SOURCE_TYPES:
            errors.append(f"sources.{key} is unknown; use {', '.join(SOURCE_TYPES)}")
    if "notion" in sources:
        for i, s in enumerate(check_list("notion", sources["notion"], errors)):
            w = f"sources.notion[{i}]"
            if not re.match(r"^https://([\w-]+\.)?notion\.(so|site)/", str(s.get("url", ""))):
                errors.append(f"{w}.url must be a https://www.notion.so/... link")
            if s.get("kind") not in NOTION_KINDS:
                errors.append(f"{w}.kind must be one of {', '.join(NOTION_KINDS)}")
            check_verified(w, s, errors, warnings)
    if "jira" in sources:
        j = sources["jira"]
        if not isinstance(j, dict):
            errors.append("sources.jira must be a mapping with site and projects/boards/jql")
        else:
            if not re.fullmatch(r"[\w.-]+\.[a-z]{2,}", str(j.get("site", ""))):
                errors.append("sources.jira.site must be a host name, e.g. acme.atlassian.net")
            keys, boards = j.get("projects") or [], j.get("boards") or []
            if not (keys or boards or j.get("jql")):
                errors.append("sources.jira needs at least one of projects, boards, jql")
            for k in keys:
                if not re.fullmatch(r"[A-Z][A-Z0-9_]+", str(k)):
                    errors.append(f"sources.jira.projects: '{k}' is not a Jira project key (e.g. PAY)")
            for b in boards:
                if not isinstance(b, int):
                    errors.append(f"sources.jira.boards: '{b}' must be a numeric board id")
            check_verified("sources.jira", j, errors, warnings)
    if "figma" in sources:
        for i, s in enumerate(check_list("figma", sources["figma"], errors)):
            w = f"sources.figma[{i}]"
            if not str(s.get("url", "")).startswith("https://www.figma.com/"):
                errors.append(f"{w}.url must be a https://www.figma.com/... link")
            if s.get("kind") not in FIGMA_KINDS:
                errors.append(f"{w}.kind must be one of {', '.join(FIGMA_KINDS)}")
            check_verified(w, s, errors, warnings)
    if "github" in sources:
        for i, s in enumerate(check_list("github", sources["github"], errors)):
            w = f"sources.github[{i}]"
            if not re.fullmatch(r"[\w.-]+/[\w.-]+", str(s.get("repo", ""))):
                errors.append(f"{w}.repo must be owner/name")
            check_verified(w, s, errors, warnings)
    if "slack" in sources:
        items = check_list("slack", sources["slack"], errors)
        for i, s in enumerate(items):
            w = f"sources.slack[{i}]"
            if not re.fullmatch(r"[CG][A-Z0-9]{8,}", str(s.get("channel", ""))):
                errors.append(f"{w}.channel must be a Slack channel id (e.g. C0C9F0ERP35), not a #name")
            use = s.get("use")
            if not isinstance(use, list) or not use or any(u not in SLACK_USES for u in use):
                errors.append(f"{w}.use must list one or both of {', '.join(SLACK_USES)}")
            check_verified(w, s, errors, warnings)
        if items and not any("context" in (s.get("use") or []) for s in items):
            warnings.append("no Slack channel has use: context, so the PM reads no team channel")


def validate_roster(roster, errors: list) -> None:
    if not isinstance(roster, list) or not roster:
        errors.append("roster must be a non-empty list")
        return
    ids = [r.get("id") for r in roster if isinstance(r, dict)]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(f"roster: duplicate id '{dup}'")
    if sum(1 for r in roster if isinstance(r, dict) and r.get("role") == "pm") != 1:
        errors.append("roster must contain exactly one pm; the PM runs the project")
    for i, r in enumerate(roster):
        w = f"roster[{i}]"
        if not isinstance(r, dict):
            errors.append(f"{w} must be a mapping")
            continue
        role = r.get("role")
        if role in STANDARD_ROLES:
            if r.get("id") != f"aor-agent-{role}" or r.get("skill") != f"aor-agent-{role}":
                errors.append(f"{w}: role {role} must have id and skill aor-agent-{role}")
        elif role == "custom":
            if not re.fullmatch(r"aor-custom-[a-z0-9-]+", str(r.get("id", ""))):
                errors.append(f"{w}.id must be aor-custom-<slug>")
            if r.get("skill") not in SPECIALIST_SKILLS:
                errors.append(f"{w}.skill must be one of {', '.join(SPECIALIST_SKILLS)} (the skill it is based on)")
            if not r.get("name"):
                errors.append(f"{w}: custom agents need a name")
        else:
            errors.append(f"{w}.role must be one of {', '.join(STANDARD_ROLES)}, custom")


def validate(proj: dict, folder: str | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for key in proj:
        if key not in TOP_KEYS:
            errors.append(f"unknown key '{key}'; allowed: {', '.join(sorted(TOP_KEYS))}")
    if proj.get("schema") != SCHEMA_VERSION:
        errors.append(f"schema must be {SCHEMA_VERSION}")
    pid = str(proj.get("id", ""))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,39}", pid):
        errors.append("id must be a kebab-case slug of 2-40 characters")
    if folder is not None and pid != folder:
        errors.append(f"id '{pid}' must match its folder name '{folder}'")
    if not str(proj.get("name", "")).strip():
        errors.append("name is required")
    status = proj.get("status")
    if status not in ("active", "archived"):
        errors.append("status must be active or archived")
    if status == "archived" and not proj.get("archived_at"):
        errors.append("archived projects need archived_at")
    validate_sources(proj.get("sources"), errors, warnings)
    validate_roster(proj.get("roster"), errors)
    fire = proj.get("fire")
    if fire is not None:
        hours = fire.get("blocker_fire_hours") if isinstance(fire, dict) else None
        if not isinstance(fire, dict) or set(fire) - {"blocker_fire_hours"} or not (
            isinstance(hours, (int, float)) and not isinstance(hours, bool) and hours > 0
        ):
            errors.append("fire must be {blocker_fire_hours: <positive number>}")
    return errors, warnings


def require_valid(proj: dict, folder: str | None = None) -> list[str]:
    errors, warnings = validate(proj, folder)
    if errors:
        raise Invalid("project.yaml is invalid: " + "; ".join(errors))
    return warnings


# ---------- scaffold, checklist, signals ----------

def scaffold(root: Path, proj: dict) -> list[str]:
    base = project_dir(root, proj["id"])
    created: list[str] = []
    for name, template in MEMORY_FILES.items():
        path = base / name
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(template.format(name=proj["name"]), encoding="utf-8")
            created.append(rel(root, path))
    dirs = MEMORY_DIRS + [f"outputs/{output_dir_name(r)}" for r in proj["roster"]]
    for d in dirs:
        keep = base / d / ".gitkeep"
        if not (base / d).is_dir() or not any((base / d).iterdir()):
            keep.parent.mkdir(parents=True, exist_ok=True)
            keep.touch()
            created.append(rel(root, keep))
    return created


def to_utc(hhmm: str, tz_name: str, now: datetime) -> tuple[int, int] | None:
    """(hour, minute) in UTC for a local time today, or None when the conversion would shift the weekday."""
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(tz_name)
    except Exception:
        return None
    h, m = (int(x) for x in hhmm.split(":"))
    local = now.astimezone(tz).replace(hour=h, minute=m, second=0, microsecond=0)
    utc = local.astimezone(timezone.utc)
    return None if utc.date() != local.date() else (utc.hour, utc.minute)


def checklist(proj: dict, cfg: dict, now: datetime) -> str:
    pid, tz = proj["id"], cfg["aor_timezone"]
    src = proj["sources"]
    standup, eod = cfg["aor_standup_time"], cfg["aor_eod_time"]

    def when(hhmm: str) -> str:
        utc = to_utc(hhmm, tz, now)
        cron = f" (UTC cron `{utc[1]} {utc[0]} * * {WORKDAYS_CRON}`)" if utc else ""
        return f"Mon–Fri {hhmm} {tz}{cron}"

    run = "Use this run's id as AOR_RUN_ID."
    rows = [
        (f"aor {pid} stand-up", when(standup), f"Run aor-agent-pm --pulse --task standup --project {pid}. {run}"),
        (f"aor {pid} end-of-day wrap", when(eod), f"Run aor-agent-pm --pulse --task eod --project {pid}. {run}"),
    ]
    if "github" in src:
        repos = ", ".join(s["repo"] for s in src["github"])
        rows.append((f"aor {pid} GitHub events", f"GitHub: pull request opened, updated, or merged; check run failed — on {repos}",
                     f"Run aor-agent-pm --pulse --task triage --project {pid} on this GitHub event. {run}"))
    context = [s for s in src.get("slack", []) if "context" in s.get("use", [])]
    if context:
        chans = ", ".join(s.get("name") or s["channel"] for s in context)
        rows.append((f"aor {pid} Slack context", f"Slack: new message in {chans}",
                     f"Run aor-agent-pm --pulse --task triage --project {pid} on this Slack message. {run}"))
    polled = [t for t in ("jira", "figma", "notion") if t in src]
    if polled:
        start, end = to_utc(standup, tz, now), to_utc(eod, tz, now)
        cron = f" (UTC cron `0 {start[0]}-{end[0]} * * {WORKDAYS_CRON}`)" if start and end and start[0] < end[0] else ""
        rows.append((f"aor {pid} source poll", f"Hourly, Mon–Fri {standup}–{eod} {tz}{cron}",
                     f"Run aor-agent-pm --pulse --task triage --project {pid} as a poll of its {', '.join(polled)} sources. {run}"))
    lines = [
        f"# Automations for {proj['name']} (`{pid}`)",
        "",
        f"Create each in the Cursor dashboard (Cloud Agents → Automations) on the `{cfg['aor_ops_repo']}` repo, default branch.",
        "Regenerate with `project_registry.py checklist` after sources change.",
        "",
        "| Automation | Trigger | Prompt |",
        "|---|---|---|",
        *[f"| {a} | {t} | {p} |" for a, t, p in rows],
    ]
    if proj["status"] == "archived":
        lines[2:2] = ["", "**Project archived: disable every automation below.**"]
    return "\n".join(lines) + "\n"


def write_checklist(root: Path, proj: dict, cfg: dict, now: datetime) -> tuple[str, str]:
    text = checklist(proj, cfg, now)
    path = project_dir(root, proj["id"]) / "automations.md"
    path.write_text(text, encoding="utf-8")
    return rel(root, path), text


def signals(pid: str, entries: list[dict], status: str, task: str) -> list[list[str]]:
    return [["status", "--project", pid, "--agent", e["id"], "--status", status, "--task", task] for e in entries]


# ---------- commands ----------

def build_from_spec(spec: dict, today: str) -> dict:
    name = str(spec.get("name", "")).strip()
    if not name:
        raise Invalid("spec needs name")
    roster_spec = spec.get("roster") or [{"role": r} for r in STANDARD_ROLES]
    roster = [roster_entry(r.get("role", ""), r.get("name"), r.get("based_on"), r.get("persona")) for r in roster_spec]
    proj = {
        "schema": SCHEMA_VERSION,
        "id": spec.get("id") or slugify(name),
        "name": name,
        "status": "active",
        "created_at": today,
        "sources": spec.get("sources"),
        "roster": roster,
    }
    if spec.get("fire") is not None:
        proj["fire"] = spec["fire"]
    if spec.get("notes"):
        proj["notes"] = spec["notes"]
    return proj


def cmd_onboard(args, root: Path, now: datetime, cfg: dict) -> dict:
    proj = build_from_spec(read_spec(args.spec), now.date().isoformat())
    if (project_dir(root, proj["id"]) / "project.yaml").exists():
        raise Invalid(f"project '{proj['id']}' already exists; use update-sources or add-agent, or archive --restore")
    warnings = require_valid(proj)
    changed = [save_project(root, proj), *scaffold(root, proj)]
    path, text = write_checklist(root, proj, cfg, now)
    changed.append(path)
    return {"ok": True, "project": proj["id"], "changed": changed, "warnings": warnings,
            "room_signals": signals(proj["id"], proj["roster"], "idle", "Joined the room"), "checklist": text}


def cmd_update_sources(args, root: Path, now: datetime, cfg: dict) -> dict:
    proj = load_project(root, args.project)
    patch = read_spec(args.spec).get("sources")
    if not isinstance(patch, dict) or not patch:
        raise Invalid('spec needs {"sources": {<type>: <new value or null to remove>}}')
    sources = dict(proj.get("sources") or {})
    before = {k: sources.get(k) for k in patch}
    for key, value in patch.items():
        if value is None:
            sources.pop(key, None)
        else:
            sources[key] = value
    proj["sources"] = sources
    warnings = require_valid(proj, args.project)
    changed = [save_project(root, proj)]
    path, text = write_checklist(root, proj, cfg, now)
    changed.append(path)
    updated = sorted(k for k in patch if before[k] != sources.get(k))
    return {"ok": True, "project": proj["id"], "updated": updated, "changed": changed, "warnings": warnings,
            "room_signals": signals(proj["id"], [e for e in proj["roster"] if e["role"] == "pm"], "idle", f"Sources updated: {', '.join(updated) or 'no change'}"),
            "checklist": text}


def cmd_add_agent(args, root: Path, now: datetime, cfg: dict) -> dict:
    proj = load_project(root, args.project)
    entry = roster_entry(args.role, args.name, args.based_on, args.persona)
    if any(e.get("id") == entry["id"] for e in proj.get("roster", [])):
        raise Invalid(f"{entry['id']} is already on {args.project}'s roster")
    proj["roster"] = [*proj.get("roster", []), entry]
    warnings = require_valid(proj, args.project)
    changed = [save_project(root, proj), *scaffold(root, proj)]
    return {"ok": True, "project": proj["id"], "agent": entry, "changed": changed, "warnings": warnings,
            "room_signals": signals(proj["id"], [entry], "idle", "Joined the room")}


def cmd_archive(args, root: Path, now: datetime, cfg: dict) -> dict:
    proj = load_project(root, args.project)
    if args.restore:
        if proj.get("status") != "archived":
            raise Invalid(f"{args.project} is not archived")
        proj["status"] = "active"
        proj.pop("archived_at", None)
        status, task = "idle", "Back in the room"
    else:
        if proj.get("status") == "archived":
            raise Invalid(f"{args.project} is already archived (since {proj.get('archived_at')})")
        proj["status"] = "archived"
        proj["archived_at"] = now.date().isoformat()
        status, task = "offline", "Left the room: project archived"
    warnings = require_valid(proj, args.project)
    changed = [save_project(root, proj)]
    path, text = write_checklist(root, proj, cfg, now)
    changed.append(path)
    return {"ok": True, "project": proj["id"], "status": proj["status"], "changed": changed, "warnings": warnings,
            "room_signals": signals(proj["id"], proj["roster"], status, task), "checklist": text}


def cmd_validate(args, root: Path, now: datetime, cfg: dict) -> dict:
    if args.all:
        ids = [p.parent.name for p in sorted((root / PROJECTS_DIR).glob("*/project.yaml"))]
    elif args.project:
        ids = [args.project]
    else:
        raise Invalid("pass --project <id> or --all")
    results, created = {}, []
    for pid in ids:
        try:
            proj = load_project(root, pid)
        except Invalid as exc:
            results[pid] = {"valid": False, "errors": [str(exc)], "warnings": []}
            continue
        errors, warnings = validate(proj, pid)
        results[pid] = {"valid": not errors, "errors": errors, "warnings": warnings}
        if args.scaffold and not errors:
            created += scaffold(root, proj)
    ok = all(r["valid"] for r in results.values())
    out = {"ok": ok, "projects": results, "changed": created}
    if not ok:
        raise Rejected(out)
    return out


def cmd_checklist(args, root: Path, now: datetime, cfg: dict) -> dict:
    proj = load_project(root, args.project)
    require_valid(proj, args.project)
    path, text = write_checklist(root, proj, cfg, now)
    return {"ok": True, "project": proj["id"], "changed": [path], "checklist": text}


def cmd_list(args, root: Path, now: datetime, cfg: dict) -> dict:
    out = []
    for p in sorted((root / PROJECTS_DIR).glob("*/project.yaml")):
        try:
            proj = load_project(root, p.parent.name)
            out.append({"id": proj.get("id"), "name": proj.get("name"), "status": proj.get("status"),
                        "roster": [e.get("id") for e in proj.get("roster", []) if isinstance(e, dict)],
                        "sources": sorted((proj.get("sources") or {}).keys())})
        except Invalid as exc:
            out.append({"id": p.parent.name, "error": str(exc)})
    return {"ok": True, "projects": out}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".", help="ops repo checkout (default: cwd)")
    p.add_argument("--now", help="override the clock (ISO-8601), for tests")
    p.add_argument("--verbose", action="store_true", help="raise on errors instead of printing JSON")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("onboard", help="register a new project from a JSON spec")
    s.add_argument("--spec", required=True,
                   help='JSON file or - for stdin: {"name", "id"?, "sources", "roster"?: [{"role", "name"?, "based_on"?, "persona"?}], '
                        '"fire"?: {"blocker_fire_hours"}, "notes"?}. Roster defaults to pm + the six specialists')
    s = sub.add_parser("update-sources", help="replace whole source types on a project")
    s.add_argument("--project", required=True)
    s.add_argument("--spec", required=True, help='JSON: {"sources": {<type>: <full new value> | null to remove}}')
    s = sub.add_parser("add-agent", help="add a standard role or a custom agent to a project's roster")
    s.add_argument("--project", required=True)
    s.add_argument("--role", required=True, help=f"{', '.join(STANDARD_ROLES)}, or custom")
    s.add_argument("--name", help="display name; required for custom")
    s.add_argument("--based-on", help=f"custom only: {', '.join(SPECIALIST_SKILLS)}")
    s.add_argument("--persona", help="persona notes layered on the base skill")
    s = sub.add_parser("archive", help="archive a project in place (or --restore it)")
    s.add_argument("--project", required=True)
    s.add_argument("--restore", action="store_true")
    s = sub.add_parser("validate", help="check project.yaml; --scaffold creates missing memory files, never overwrites")
    s.add_argument("--project")
    s.add_argument("--all", action="store_true")
    s.add_argument("--scaffold", action="store_true")
    s = sub.add_parser("checklist", help="regenerate the project's automations.md")
    s.add_argument("--project", required=True)
    sub.add_parser("list", help="list registered projects")
    return p


COMMANDS = {
    "onboard": cmd_onboard,
    "update-sources": cmd_update_sources,
    "add-agent": cmd_add_agent,
    "archive": cmd_archive,
    "validate": cmd_validate,
    "checklist": cmd_checklist,
    "list": cmd_list,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    try:
        now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        out = COMMANDS[args.cmd](args, root, now, load_config(root))
    except Rejected as exc:
        print(json.dumps(exc.payload, ensure_ascii=False, indent=2))
        return 1
    except Invalid as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    except Exception as exc:
        if args.verbose:
            raise
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
