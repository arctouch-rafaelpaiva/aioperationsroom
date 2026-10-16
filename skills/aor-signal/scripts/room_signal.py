#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""aor-signal: the single writer of AI Operations Room state.

Every write is an append-only event in {root}/aor/room/events/YYYY-MM-DD/{run-id}.jsonl.
One file per run means concurrent cloud runs never conflict in git. Current state
(agents, asks, approvals, risks, fires, digests, project health) is folded from all
event files on demand. New events are also pushed live to the room at
$AOR_ROOM_URL/api/events (Bearer $AOR_ROOM_TOKEN); a failed push never fails the
command, because git stays the source of truth and the room reconciles from it.

Config: aor_* keys from the aor section of {root}/_bmad/config.yaml (written by aor-setup)
(aor_timezone, aor_blocker_fire_hours, aor_slack_batch_minutes, aor_quiet_hours).
Per-project `blocker_fire_hours: N` in
{root}/_bmad/memory/aor/projects/{project}/project.yaml overrides the fire threshold.

Env: AOR_RUN_ID names this run's event file (default "local"). AOR_ROOM_URL and
AOR_ROOM_TOKEN enable the live push.

Output: JSON on stdout. Exit codes: 0 ok, 1 invalid request (message names the fix),
2 error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA_VERSION = 1
STATUSES = ["idle", "working", "reading", "drafting", "meeting", "wrapping", "offline"]
TARGETS = ["jira", "notion", "github", "figma", "slack"]
OPERATOR_DECISIONS = ["answered", "approved", "edited", "rejected"]
AGENT_DECISIONS = ["done", "failed"]
TERMINAL = {"answered", "rejected", "done", "failed"}
# The operator may still reject or re-edit an approved item until the agent posts it.
TRANSITIONS = {
    ("ask", "open"): ["answered", "rejected"],
    ("approval", "open"): ["approved", "edited", "rejected"],
    ("approval", "approved"): ["done", "failed", "edited", "rejected"],
    ("approval", "edited"): ["done", "failed", "edited", "rejected"],
}
FIRE_REASONS = ["failed_build", "missed_deadline", "client_escalation", "blocker_overdue", "other"]
DEFAULTS = {
    "aor_timezone": "America/Sao_Paulo",
    "aor_blocker_fire_hours": "24",
    "aor_slack_batch_minutes": "30",
    "aor_quiet_hours": "19:00-07:30",
}


class Invalid(Exception):
    """A request the caller can fix; exits 1 with the message."""


# ---------- time ----------

def parse_ts(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def fmt_ts(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def local_tz(name: str):
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:
        print(f"warning: timezone {name!r} unavailable, using UTC-3", file=sys.stderr)
        return timezone(timedelta(hours=-3))


def in_quiet_hours(now: datetime, spec: str, tz) -> bool:
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*", spec or "")
    if not m:
        return False
    start = int(m[1]) * 60 + int(m[2])
    end = int(m[3]) * 60 + int(m[4])
    local = now.astimezone(tz)
    minute = local.hour * 60 + local.minute
    if start <= end:
        return start <= minute < end
    return minute >= start or minute < end


# ---------- config ----------

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


def load_config(root: Path) -> dict[str, str]:
    cfg = dict(DEFAULTS)
    cfg.update({k: v for k, v in aor_config(root).items() if k in DEFAULTS})
    return cfg


def blocker_hours(root: Path, project: str, cfg: dict[str, str]) -> float:
    project_yaml = root / "_bmad" / "memory" / "aor" / "projects" / project / "project.yaml"
    if project_yaml.is_file():
        m = re.search(r"^\s*blocker_fire_hours\s*:\s*(\d+(?:\.\d+)?)", project_yaml.read_text(encoding="utf-8"), re.M)
        if m:
            return float(m[1])
    return float(cfg["aor_blocker_fire_hours"])


# ---------- events ----------

def room_dir(root: Path) -> Path:
    return root / "aor" / "room"


def new_id(prefix: str, now: datetime) -> str:
    return f"{prefix}-{now.strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3)}"


def run_id() -> str:
    raw = os.environ.get("AOR_RUN_ID") or "local"
    return re.sub(r"[^A-Za-z0-9._-]", "-", raw)[:80]


def read_events(root: Path) -> list[dict]:
    events: list[dict] = []
    base = room_dir(root) / "events"
    if not base.is_dir():
        return events
    for path in sorted(base.rglob("*.jsonl")):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"warning: skipping bad line {path}:{n}", file=sys.stderr)
    # Stable sort on ts alone: same-second events keep their append order, which is causal within a run.
    events.sort(key=lambda e: e.get("ts", ""))
    return events


def make_event(etype: str, now: datetime, project: str | None, agent: str | None, data: dict, eid: str | None = None) -> dict:
    return {
        "v": SCHEMA_VERSION,
        "id": eid or new_id("ev", now),
        "ts": fmt_ts(now),
        "type": etype,
        "project": project,
        "agent": agent,
        "run": run_id(),
        "data": data,
    }


def append_events(root: Path, events: list[dict]) -> Path:
    day = events[0]["ts"][:10]
    path = room_dir(root) / "events" / day / f"{run_id()}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def push(events: list[dict], disabled: bool) -> str:
    url = os.environ.get("AOR_ROOM_URL", "").rstrip("/")
    if disabled or not url:
        return "skipped"
    body = json.dumps({"events": events}).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/api/events",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('AOR_ROOM_TOKEN', '')}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return "ok" if 200 <= resp.status < 300 else f"failed:{resp.status}"
    except Exception as exc:  # the room catches up from git
        print(f"warning: live push failed ({exc}); event kept in git", file=sys.stderr)
        return "failed"


# ---------- state ----------

def fire_key(project: str | None, reason: str, ref: str | None) -> str:
    return f"{project}|{reason}|{ref or ''}"


def risk_key(project: str | None, risk: str | None) -> str:
    return f"{project}|{risk}"


def fold(events: list[dict]) -> dict:
    agents: dict[str, dict] = {}
    items: dict[str, dict] = {}
    risks: dict[str, dict] = {}
    fires: dict[str, dict] = {}
    digested: set[str] = set()
    last_digest: str | None = None
    projects: set[str] = set()
    early_resolves: dict[str, list[dict]] = {}

    def apply_resolve(item: dict, d: dict, ts: str) -> None:
        # Hand-written or room-written lines bypass cmd_resolve, so enforce the same transitions here.
        if d.get("decision") not in TRANSITIONS.get((item["kind"], item["status"]), []):
            print(f"warning: ignoring illegal resolve {item['status']}->{d.get('decision')} on {item['id']}", file=sys.stderr)
            return
        item["status"] = d.get("decision")
        item["resolved_at"] = ts
        for k in ("answer", "payload", "by", "note", "result_url"):
            if d.get(k) is not None:
                item["final_payload" if k == "payload" else k] = d[k]

    for e in events:
        t, p, a, d, ts = e.get("type"), e.get("project"), e.get("agent"), e.get("data") or {}, e.get("ts")
        if p:
            projects.add(p)
        if t == "status":
            agents[f"{p}/{a}"] = {"project": p, "agent": a, "updated_at": ts, **d}
        elif t in ("ask", "approval"):
            items[e["id"]] = {"id": e["id"], "kind": t, "project": p, "owner": a, "created_at": ts, "status": "open", **d}
            for rd, rts in early_resolves.pop(e["id"], []):
                apply_resolve(items[e["id"]], rd, rts)
        elif t == "resolve":
            # A resolve from another run can share a timestamp with its item and sort first.
            item = items.get(d.get("item"))
            if item:
                apply_resolve(item, d, ts)
            else:
                early_resolves.setdefault(d.get("item"), []).append((d, ts))
        elif t == "risk_open":
            risks[risk_key(p, d["risk"])] = {"risk": d["risk"], "project": p, "owner": a, "opened_at": ts, "open": True, **d}
        elif t == "risk_close":
            if risk_key(p, d.get("risk")) in risks:
                risks[risk_key(p, d["risk"])].update(open=False, closed_at=ts)
        elif t == "fire":
            key = fire_key(p, d.get("reason"), d.get("ref"))
            fires[key] = {"key": key, "project": p, "raised_by": a, "since": ts, "active": True, **d}
        elif t == "fire_clear":
            key = fire_key(p, d.get("reason"), d.get("ref"))
            if key in fires:
                fires[key].update(active=False, cleared_at=ts)
        elif t == "digest_sent":
            if d.get("items"):
                digested.update(d["items"])
                last_digest = ts
            for key in d.get("fires") or []:
                if key in fires and fires[key]["active"]:
                    fires[key]["alerted_at"] = ts

    health = {}
    for proj in sorted(projects):
        active = [f for f in fires.values() if f["project"] == proj and f["active"]]
        open_items = [i for i in items.values() if i["project"] == proj and i["status"] == "open"]
        if active:
            level = "red"
        elif open_items:
            level = "amber"
        else:
            level = "green"
        health[proj] = {
            "health": level,
            "fires": [f["reason"] for f in active],
            "needs_you": sum(1 for i in open_items if i["kind"] == "ask"),
            "approvals": sum(1 for i in open_items if i["kind"] == "approval"),
        }

    return {
        "agents": agents,
        "items": items,
        "risks": risks,
        "fires": fires,
        "projects": health,
        "digested": sorted(digested),
        "last_digest_at": last_digest,
    }


# ---------- commands ----------

def load_json_arg(raw: str | None, file: str | None, label: str):
    if file:
        raw = Path(file).read_text(encoding="utf-8")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw  # plain text payloads (comment bodies) are allowed


def record(args, root: Path, events: list[dict], extra: dict | None = None) -> dict:
    path = append_events(root, events)
    out = {"ok": True, "events": [e["id"] for e in events], "file": str(path.relative_to(root)), "push": push(events, args.no_push)}
    out.update(extra or {})
    return out


def cmd_status(args, root, now):
    data = {"status": args.status, "task": args.task}
    if args.source_url:
        data["source_url"] = args.source_url
    return record(args, root, [make_event("status", now, args.project, args.agent, data)])


def cmd_ask(args, root, now):
    data = {"question": args.question}
    if args.options:
        data["options"] = [o.strip() for o in args.options.split("|") if o.strip()]
    if args.context_url:
        data["context_url"] = args.context_url
    ev = make_event("ask", now, args.project, args.agent, data, eid=new_id("q", now))
    return record(args, root, [ev], {"item": ev["id"]})


def cmd_approval(args, root, now):
    payload = load_json_arg(args.payload, args.payload_file, "payload")
    if payload in (None, ""):
        raise Invalid("approval needs the exact content to post: pass --payload or --payload-file")
    data = {"target": args.target, "action": args.action, "payload": payload, "preview": args.preview, "rationale": args.rationale}
    if args.target_url:
        data["target_url"] = args.target_url
    ev = make_event("approval", now, args.project, args.agent, data, eid=new_id("ap", now))
    return record(args, root, [ev], {"item": ev["id"]})


def cmd_resolve(args, root, now):
    state = fold(read_events(root))
    item = state["items"].get(args.item)
    if not item:
        known = [i for i, v in state["items"].items() if v["status"] in ("open", "approved", "edited")]
        raise Invalid(f"item {args.item!r} not found; open or actionable items: {known or 'none'}")
    if item["status"] in TERMINAL:
        raise Invalid(f"item {args.item} is already {item['status']} (final); raise a new ask or approval instead")
    allowed = TRANSITIONS.get((item["kind"], item["status"]), [])
    if args.decision not in allowed:
        raise Invalid(f"{item['kind']} is {item['status']}; allowed decisions now: {allowed}")
    if args.decision == "edited" and not (args.payload or args.payload_file):
        raise Invalid("edited needs the edited content: pass --payload or --payload-file")
    data = {"item": args.item, "decision": args.decision, "by": args.by}
    if args.answer:
        data["answer"] = args.answer
    if args.note:
        data["note"] = args.note
    if args.result_url:
        data["result_url"] = args.result_url
    payload = load_json_arg(args.payload, args.payload_file, "payload")
    if payload is not None:
        data["payload"] = payload
    return record(args, root, [make_event("resolve", now, item["project"], args.by, data)])


def cmd_risk(args, root, now):
    if args.action == "open":
        if not args.title:
            raise Invalid("risk open needs --title")
        rid = args.risk or new_id("rk", now)
        data = {"risk": rid, "title": args.title, "kind": args.kind, "severity": args.severity}
        if args.ref:
            data["ref"] = args.ref
        return record(args, root, [make_event("risk_open", now, args.project, args.agent, data)], {"risk": rid})
    state = fold(read_events(root))
    risk = state["risks"].get(risk_key(args.project, args.risk))
    if not risk or not risk["open"]:
        open_ids = [v["risk"] for v in state["risks"].values() if v["open"] and v["project"] == args.project]
        raise Invalid(f"risk {args.risk!r} is not open; open risks for {args.project}: {open_ids or 'none'}")
    return record(args, root, [make_event("risk_close", now, args.project, args.agent, {"risk": args.risk})])


def cmd_fire(args, root, now):
    state = fold(read_events(root))
    key = fire_key(args.project, args.reason, args.ref)
    if args.clear:
        if key not in state["fires"] or not state["fires"][key]["active"]:
            active = [f.get("ref") for f in state["fires"].values()
                      if f["active"] and f["project"] == args.project and f.get("reason") == args.reason]
            raise Invalid(f"no active {args.reason} fire for {args.project} with ref {args.ref!r}; active refs: {active or 'none'}")
        data = {"reason": args.reason, "ref": args.ref}
        return record(args, root, [make_event("fire_clear", now, args.project, args.agent, data)], {"recorded": True})
    if key in state["fires"] and state["fires"][key]["active"]:
        return {"ok": True, "recorded": False, "alert": False, "note": "fire already active; no new alert"}
    if not args.detail:
        raise Invalid("fire needs --detail describing what is burning")
    data = {"reason": args.reason, "detail": args.detail, "ref": args.ref}
    return record(args, root, [make_event("fire", now, args.project, args.agent, data)], {"recorded": True, "alert": True})


def cmd_evaluate(args, root, now):
    cfg = load_config(root)
    state = fold(read_events(root))
    new_events: list[dict] = []
    new_fires = []
    for risk in state["risks"].values():
        rid = risk["risk"]
        key = fire_key(risk["project"], "blocker_overdue", rid)
        active = key in state["fires"] and state["fires"][key]["active"]
        if risk["open"] and risk.get("kind") == "blocker":
            hours = blocker_hours(root, risk["project"], cfg)
            age = (now - parse_ts(risk["opened_at"])).total_seconds() / 3600
            if age >= hours and not active:
                detail = f"blocker open {age:.0f}h (threshold {hours:g}h): {risk.get('title', rid)}"
                data = {"reason": "blocker_overdue", "detail": detail, "ref": rid}
                new_events.append(make_event("fire", now, risk["project"], "aor-signal", data))
                new_fires.append({"project": risk["project"], **data})
        elif not risk["open"] and active:
            new_events.append(make_event("fire_clear", now, risk["project"], "aor-signal", {"reason": "blocker_overdue", "ref": rid}))
    out: dict = {"ok": True, "new_fires": new_fires}
    if new_events:
        out.update(record(args, root, new_events))
        state = fold(read_events(root))
    out["projects"] = state["projects"]
    return out


def item_summary(item: dict) -> dict:
    text = item.get("question") if item["kind"] == "ask" else (item.get("preview") or f"{item.get('action')} on {item.get('target')}")
    return {"id": item["id"], "kind": item["kind"], "project": item["project"], "owner": item["owner"], "summary": text, "created_at": item["created_at"]}


def cmd_digest(args, root, now):
    cfg = load_config(root)
    state = fold(read_events(root))
    if args.mark_sent or args.mark_alerted:
        ids = [i.strip() for i in (args.mark_sent or "").split(",") if i.strip()]
        keys = [k.strip() for k in (args.mark_alerted or "").split(",") if k.strip()]
        unknown = [i for i in ids if i not in state["items"]]
        if unknown:
            raise Invalid(f"unknown item ids: {unknown}")
        inactive = [k for k in keys if k not in state["fires"] or not state["fires"][k]["active"]]
        if inactive:
            raise Invalid(f"no active fire for keys {inactive}; take keys from digest's fires_to_alert")
        data = {"items": ids, "fires": keys, "channel": args.channel, "thread_ts": args.thread_ts}
        return record(args, root, [make_event("digest_sent", now, None, "aor-agent-maestro", data)])

    # Fires ignore quiet hours and the batch window: they are always returned until marked alerted.
    fires_to_alert = [f for f in state["fires"].values() if f["active"] and not f.get("alerted_at")]
    pending = [item_summary(i) for i in state["items"].values() if i["status"] == "open" and i["id"] not in state["digested"]]
    out = {"ok": True, "send": False, "pending": len(pending), "fires_to_alert": fires_to_alert}
    if not pending:
        return {**out, "reason": "nothing new"}
    if in_quiet_hours(now, cfg["aor_quiet_hours"], local_tz(cfg["aor_timezone"])):
        return {**out, "reason": f"quiet hours {cfg['aor_quiet_hours']}"}
    window = timedelta(minutes=float(cfg["aor_slack_batch_minutes"]))
    if state["last_digest_at"] and now - parse_ts(state["last_digest_at"]) < window:
        return {**out, "reason": "batch window open", "next_at": fmt_ts(parse_ts(state["last_digest_at"]) + window)}
    by_project: dict[str, list] = {}
    for p in pending:
        by_project.setdefault(p["project"], []).append(p)
    return {**out, "send": True, "items": pending, "by_project": by_project}


def cmd_state(args, root, now):
    state = fold(read_events(root))
    if args.section == "items":
        items = list(state["items"].values())
        if args.id:
            items = [i for i in items if i["id"] == args.id]
        if args.status:
            items = [i for i in items if i["status"] == args.status]
        if args.owner:
            items = [i for i in items if i["owner"] == args.owner]
        if args.project:
            items = [i for i in items if i["project"] == args.project]
        if args.kind:
            items = [i for i in items if i["kind"] == args.kind]
        return {"ok": True, "items": items}
    if args.section:
        return {"ok": True, args.section: state[args.section]}
    return {"ok": True, **state}


# ---------- cli ----------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".", help="ops repo root (default: cwd)")
    p.add_argument("--now", help="ISO timestamp to use as now (testing/replay)")
    p.add_argument("--no-push", action="store_true", help="skip the live push to the room")
    p.add_argument("--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    def who(sp, agent_required=True):
        sp.add_argument("--project", required=True, help="project id (folder under _bmad/memory/aor/projects)")
        sp.add_argument("--agent", required=agent_required, help="skill name of the acting agent, e.g. aor-agent-qa")

    s = sub.add_parser("status", help="set an agent's room status and current task")
    who(s)
    s.add_argument("--status", required=True, choices=STATUSES)
    s.add_argument("--task", required=True, help="one line: what the agent is doing now")
    s.add_argument("--source-url", help="link to the ticket/file/PR/page being worked")

    s = sub.add_parser("ask", help="raise a needs-you question for the operator (speech bubble)")
    who(s)
    s.add_argument("--question", required=True)
    s.add_argument("--options", help="pipe-separated suggested answers")
    s.add_argument("--context-url")

    s = sub.add_parser("approval", help="raise hand: queue an external post for operator approval")
    who(s)
    s.add_argument("--target", required=True, choices=TARGETS)
    s.add_argument("--action", required=True, help="e.g. comment, create_issue, update_page, post_message")
    s.add_argument("--target-url", help="where it will be posted")
    s.add_argument("--preview", required=True, help="one line shown in room and Slack digest")
    s.add_argument("--rationale", required=True, help="why this post is needed")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--payload", help="exact content to post (JSON or text)")
    g.add_argument("--payload-file", help="file holding the exact content to post")

    s = sub.add_parser("resolve", help="record an operator decision or an agent's post outcome")
    s.add_argument("--item", required=True)
    s.add_argument("--decision", required=True, choices=OPERATOR_DECISIONS + AGENT_DECISIONS,
                   help="ask: answered|rejected. approval: approved|edited|rejected, then the agent records done|failed. "
                        "Final states (answered, rejected, done, failed) accept nothing further")
    s.add_argument("--by", required=True, help="operator, room, slack, or the agent skill name")
    s.add_argument("--answer")
    s.add_argument("--note")
    s.add_argument("--result-url", help="link to the posted result (done)")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--payload")
    g.add_argument("--payload-file")

    s = sub.add_parser("risk", help="open or close a blocker/risk")
    s.add_argument("action", choices=["open", "close"])
    who(s)
    s.add_argument("--risk", help="risk id (required for close; optional stable id for open)")
    s.add_argument("--title")
    s.add_argument("--kind", default="blocker", choices=["blocker", "risk"])
    s.add_argument("--severity", default="medium", choices=["low", "medium", "high", "critical"])
    s.add_argument("--ref", help="link to the source ticket/PR")

    s = sub.add_parser("fire", help="flag (or --clear) a project fire; deduped per project/reason/ref")
    who(s)
    s.add_argument("--reason", required=True, choices=FIRE_REASONS)
    s.add_argument("--detail")
    s.add_argument("--ref", help="what it is about (build URL, ticket, client thread)")
    s.add_argument("--clear", action="store_true")

    sub.add_parser("evaluate", help="recompute project health; raise/clear blocker_overdue fires")

    s = sub.add_parser("digest", help="grouped Slack digest of new asks/approvals (batch window, quiet hours) plus fires_to_alert (always)")
    s.add_argument("--mark-sent", help="comma-separated item ids that were just posted")
    s.add_argument("--mark-alerted", help="comma-separated fire keys (project|reason|ref) whose alert was just posted")
    s.add_argument("--channel")
    s.add_argument("--thread-ts", help="Slack thread the digest was posted in")

    s = sub.add_parser("state", help="folded room state as JSON")
    s.add_argument("section", nargs="?", choices=["agents", "items", "risks", "fires", "projects"])
    s.add_argument("--id", help="items: one item by id (re-check right before posting)")
    s.add_argument("--status")
    s.add_argument("--owner")
    s.add_argument("--project")
    s.add_argument("--kind", choices=["ask", "approval"])
    return p


COMMANDS = {
    "status": cmd_status,
    "ask": cmd_ask,
    "approval": cmd_approval,
    "resolve": cmd_resolve,
    "risk": cmd_risk,
    "fire": cmd_fire,
    "evaluate": cmd_evaluate,
    "digest": cmd_digest,
    "state": cmd_state,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    try:
        now = parse_ts(args.now) if args.now else datetime.now(timezone.utc)
        out = COMMANDS[args.cmd](args, root, now)
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
