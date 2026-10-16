#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""aor-agent-pm: project memory helper for the AI Operations Room.

Project memory lives in {root}/_bmad/memory/aor/projects/{project}/ and is shared by
the PM and its specialists. Concurrent cloud runs must never write the same file, so:

- daily/<local date>/<run-id>.md   append-only log, one file per run (`log`)
- inbox/<item-id>.md               one file per routed item, status in frontmatter (`inbox`)
- index.md, decisions.md, risks.md, open-questions.md, standup/, eod/, weekly/
                                   curated by the PM only

Commands:
  context  the project's working set (registry, curated files, open inbox, recent logs)
  log      append a role-tagged line to this run's daily log
  inbox    add (deduped by --key) | list | set
  sync     commit project memory (squad memory included) + aor/room/ + an optional cross-project sanctum, rebase, push with retry

Env: AOR_RUN_ID names this run's files (default "local").
Config: aor_timezone from {root}/_bmad/aor/config.yaml (flat key: value).
Output: JSON on stdout (context --format md prints markdown). Exit codes: 0 ok,
1 invalid request (message names the fix), 2 error (sync: conflict or push failure).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECTS = Path("_bmad/memory/aor/projects")
MEMORY_ROOT = Path("_bmad/memory")
ROOM = Path("aor/room")
STATUSES = ["new", "routed", "done", "dropped"]
ROLES = ["pm", "discovery", "requirements", "docs", "design", "engineering", "qa", "maestro", "operator"]
CURATED = ["index.md", "open-questions.md", "risks.md", "decisions.md"]
CONTEXT_CHAR_BUDGET = 14000


class Invalid(Exception):
    pass


class Failed(Exception):
    def __init__(self, payload: dict):
        super().__init__(payload.get("error", "failed"))
        self.payload = payload


# ---------- basics ----------

def read_flat(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*?)\s*$", line)
            if m and m[2]:
                out[m[1]] = m[2].strip().strip("'\"")
    return out


def local_tz(root: Path):
    name = read_flat(root / "_bmad" / "aor" / "config.yaml").get("aor_timezone", "America/Sao_Paulo")
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:
        return timezone.utc


def run_id() -> str:
    rid = os.environ.get("AOR_RUN_ID", "local")
    if not re.fullmatch(r"[\w.-]{1,80}", rid):
        raise Invalid("AOR_RUN_ID may only contain letters, digits, '.', '_' and '-'")
    return rid


def project_dir(root: Path, project: str) -> Path:
    base = root / PROJECTS / project
    if not (base / "project.yaml").is_file():
        known = ", ".join(sorted(p.parent.name for p in (root / PROJECTS).glob("*/project.yaml"))) or "none"
        raise Invalid(f"no project '{project}' (known: {known}); onboard it with aor-onboard-project")
    return base


def active_projects(root: Path) -> list[str]:
    out = []
    for p in sorted((root / PROJECTS).glob("*/project.yaml")):
        if re.search(r"^status:\s*active\s*$", p.read_text(encoding="utf-8"), re.M):
            out.append(p.parent.name)
    return out


def one_line(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


# ---------- inbox ----------

def parse_item(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {"id": path.stem, "status": "invalid", "title": path.stem, "file": path.name}
    meta = {}
    for line in m[1].splitlines():
        key, _, value = line.partition(":")
        if key.strip():
            meta[key.strip()] = value.strip()
    body = m[2].strip()
    title = body.splitlines()[0].lstrip("# ").strip() if body else meta.get("id", path.stem)
    return {**meta, "title": title, "body": "\n".join(body.splitlines()[1:]).strip(), "file": path.name}


def write_item(path: Path, item: dict) -> None:
    keys = ["id", "status", "role", "created_at", "updated_at", "from", "source", "ref", "key", "note"]
    head = "\n".join(f"{k}: {one_line(str(item[k]))}" for k in keys if item.get(k))
    path.write_text(f"---\n{head}\n---\n# {one_line(item['title'])}\n\n{item.get('body', '').strip()}\n", encoding="utf-8")


def all_items(base: Path) -> list[dict]:
    return [parse_item(p) for p in sorted((base / "inbox").glob("*.md"))]


def cmd_inbox(args, root: Path, now: datetime) -> dict:
    base = project_dir(root, args.project)
    (base / "inbox").mkdir(exist_ok=True)
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    if args.action == "add":
        if not args.title:
            raise Invalid("inbox add needs --title")
        if args.key:
            for item in all_items(base):
                if item.get("key") == one_line(args.key):
                    return {"ok": True, "created": False, "item": item}
        iid = f"in-{now.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2)}"
        item = {"id": iid, "status": "new", "created_at": stamp, "updated_at": stamp, "from": args.sender,
                "source": args.source, "ref": args.ref, "key": args.key, "title": args.title, "body": args.body or ""}
        write_item(base / "inbox" / f"{iid}.md", item)
        return {"ok": True, "created": True, "item": parse_item(base / "inbox" / f"{iid}.md"),
                "changed": [(base / "inbox" / f"{iid}.md").relative_to(root).as_posix()]}
    if args.action == "list":
        items = all_items(base)
        wanted = {"open": ["new", "routed"]}.get(args.status, [args.status] if args.status else None)
        if wanted:
            items = [i for i in items if i.get("status") in wanted]
        return {"ok": True, "items": [{k: v for k, v in i.items() if k != "body"} for i in items]}
    # set
    if not args.id or args.status not in STATUSES:
        raise Invalid(f"inbox set needs --id and --status ({', '.join(STATUSES)})")
    path = base / "inbox" / f"{args.id}.md"
    if not path.is_file():
        raise Invalid(f"no inbox item {args.id} in {args.project}")
    if args.status == "routed" and args.role not in ROLES:
        raise Invalid(f"routing needs --role ({', '.join(ROLES)})")
    item = parse_item(path)
    if item.get("status") in ("done", "dropped") and args.status != item.get("status"):
        raise Invalid(f"{args.id} is already {item['status']}; add a new item instead of reopening")
    item.update({"status": args.status, "updated_at": stamp})
    if args.role:
        item["role"] = args.role
    if args.note:
        item["note"] = args.note
    write_item(path, item)
    return {"ok": True, "item": parse_item(path), "changed": [path.relative_to(root).as_posix()]}


# ---------- daily log ----------

def cmd_log(args, root: Path, now: datetime) -> dict:
    base = project_dir(root, args.project)
    if args.role not in ROLES:
        raise Invalid(f"--role must be one of {', '.join(ROLES)}")
    local = now.astimezone(local_tz(root))
    path = base / "daily" / local.date().isoformat() / f"{run_id()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"- {local.strftime('%H:%M')} [{args.role}] {one_line(args.text)}"
    if args.ref:
        line += f" ({args.ref})"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return {"ok": True, "file": path.relative_to(root).as_posix(), "line": line}


# ---------- context ----------

def latest(base: Path, folder: str) -> Path | None:
    files = sorted((base / folder).glob("*.md"))
    return files[-1] if files else None


def context(root: Path, project: str, now: datetime) -> dict:
    base = project_dir(root, project)
    today = now.astimezone(local_tz(root)).date().isoformat()
    eod, standup = latest(base, "eod"), latest(base, "standup")
    days = sorted(d.name for d in (base / "daily").glob("*") if d.is_dir())
    since = eod.stem if eod else (days[-2] if len(days) >= 2 else "")
    recent = [d for d in days if d >= since] or days[-1:]
    logs = []
    for d in recent:
        for f in sorted((base / "daily" / d).glob("*.md")):
            logs.append({"file": f.relative_to(base).as_posix(), "text": f.read_text(encoding="utf-8").strip()})
    return {
        "project": project,
        "today": today,
        "active_projects": active_projects(root),
        "registry": (base / "project.yaml").read_text(encoding="utf-8").strip(),
        "curated": {name: (base / name).read_text(encoding="utf-8").strip() for name in CURATED if (base / name).is_file()},
        "latest_standup": {"file": standup.relative_to(base).as_posix(), "text": standup.read_text(encoding="utf-8").strip()} if standup else None,
        "latest_eod": {"file": eod.relative_to(base).as_posix(), "text": eod.read_text(encoding="utf-8").strip()} if eod else None,
        "open_inbox": [{k: v for k, v in i.items() if k in ("id", "status", "role", "source", "title", "ref", "created_at")}
                       for i in all_items(base) if i.get("status") in ("new", "routed")],
        "daily_logs": logs,
    }


def render_context(ctx: dict) -> str:
    out = [f"\n===== PROJECT {ctx['project']} (today {ctx['today']}) =====", "", "--- project.yaml ---", ctx["registry"]]
    for name, text in ctx["curated"].items():
        out += ["", f"--- {name} ---", text]
    for key in ("latest_standup", "latest_eod"):
        if ctx[key]:
            out += ["", f"--- {ctx[key]['file']} ---", ctx[key]["text"]]
    out += ["", f"--- inbox: {len(ctx['open_inbox'])} open ---"]
    out += [f"- {i['id']} [{i.get('status')}{'→' + i['role'] if i.get('role') else ''}] ({i.get('source', '?')}) {i['title']}"
            for i in ctx["open_inbox"]]
    out += ["", "--- daily logs since the last wrap ---"]
    used = sum(len(x) for x in out)
    for log in ctx["daily_logs"]:
        chunk = f"[{log['file']}]\n{log['text']}"
        if used + len(chunk) > CONTEXT_CHAR_BUDGET:
            out.append(f"(more logs not shown; read daily/ directly from {log['file']})")
            break
        out.append(chunk)
        used += len(chunk)
    return "\n".join(out)


def cmd_context(args, root: Path, now: datetime):
    ctx = context(root, args.project, now)
    return render_context(ctx) if args.format == "md" else {"ok": True, **ctx}


# ---------- sync ----------

def git(root: Path, *argv: str, check: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run(["git", *argv], cwd=root, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise Failed({"ok": False, "error": f"git {' '.join(argv)} failed: {res.stderr.strip() or res.stdout.strip()}"})
    return res


def cmd_sync(args, root: Path, now: datetime) -> dict:
    projects = args.project or []
    for project in projects:
        project_dir(root, project)
    if args.sanctum and not re.fullmatch(r"aor-agent-[a-z-]+", args.sanctum):
        raise Invalid("--sanctum must be an aor agent skill name, e.g. aor-agent-maestro")
    if not projects and not args.sanctum:
        raise Invalid("sync needs --project (the projects this run touched) or a cross-project --sanctum")
    wanted = [PROJECTS / p for p in projects] + [ROOM] + ([MEMORY_ROOT / args.sanctum] if args.sanctum else [])
    paths = [p for p in wanted if (root / p).exists()]
    git(root, "add", "--", *[p.as_posix() for p in paths])
    staged = git(root, "diff", "--cached", "--name-only").stdout.split()
    committed = None
    if staged:
        git(root, "commit", "-m", args.message, "-m", f"aor run: {run_id()}")
        committed = git(root, "rev-parse", "--short", "HEAD").stdout.strip()
    if args.no_push:
        return {"ok": True, "committed": committed, "files": staged, "pushed": False}
    for attempt in range(1, args.retries + 1):
        if git(root, "pull", "--rebase", check=False).returncode != 0:
            conflicts = git(root, "diff", "--name-only", "--diff-filter=U", check=False).stdout.split()
            git(root, "rebase", "--abort", check=False)
            raise Failed({"ok": False, "error": "rebase conflict; your commit is kept locally, nothing was pushed",
                          "conflicts": conflicts, "committed": committed})
        if git(root, "push", check=False).returncode == 0:
            return {"ok": True, "committed": committed, "files": staged, "pushed": True, "attempts": attempt}
        time.sleep(min(2 ** attempt, 16))
    raise Failed({"ok": False, "error": f"push failed after {args.retries} attempts", "committed": committed})


# ---------- cli ----------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".", help="ops repo checkout (default: cwd)")
    p.add_argument("--now", help="override the clock (ISO-8601), for tests")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("context", help="print the project's working set")
    s.add_argument("--project", required=True)
    s.add_argument("--format", choices=["json", "md"], default="json")

    s = sub.add_parser("log", help="append one line to this run's daily log")
    s.add_argument("--project", required=True)
    s.add_argument("--role", required=True, help=", ".join(ROLES))
    s.add_argument("--text", required=True, help="one line, e.g. 'Routed PAY-142 to requirements'")
    s.add_argument("--ref", help="link to the ticket/file/PR/page")

    s = sub.add_parser("inbox", help="add | list | set inbox items")
    s.add_argument("action", choices=["add", "list", "set"])
    s.add_argument("--project", required=True)
    s.add_argument("--title", help="add: one line naming the work")
    s.add_argument("--body", help="add: details, links, the ask")
    s.add_argument("--from", dest="sender", default="pm", help="add: who routed it (maestro, pm, operator, event)")
    s.add_argument("--source", help="add: jira, figma, github, notion, slack, email, operator")
    s.add_argument("--ref", help="add: link to the thing")
    s.add_argument("--key", help="add: dedupe key, e.g. jira|PAY-142|2026-10-16T10:02; an existing key returns that item")
    s.add_argument("--id", help="set: item id")
    s.add_argument("--status", help="list: new|routed|done|dropped|open. set: new|routed|done|dropped")
    s.add_argument("--role", help="set --status routed: the specialist role it went to")
    s.add_argument("--note", help="set: outcome or reason, one line")

    s = sub.add_parser("sync", help="commit this run's memory and room events, rebase, push")
    s.add_argument("--project", action="append", help="repeat for every project this run touched")
    s.add_argument("--sanctum", help="a cross-project sanctum to include (Maestro); squad memory is already inside each project")
    s.add_argument("--message", required=True, help="e.g. 'aor payments-app: stand-up 2026-10-16'")
    s.add_argument("--retries", type=int, default=3)
    s.add_argument("--no-push", action="store_true", help="commit only")
    return p


COMMANDS = {"context": cmd_context, "log": cmd_log, "inbox": cmd_inbox, "sync": cmd_sync}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    try:
        now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
        out = COMMANDS[args.cmd](args, root, now)
    except Invalid as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    except Failed as exc:
        print(json.dumps(exc.payload, ensure_ascii=False, indent=2))
        return 2
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
        return 2
    print(out if isinstance(out, str) else json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
