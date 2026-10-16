import type { AgentState, Decision, Fire, FoldedState, Item, ProjectHealth, Risk, RoomEvent } from "./types";

// Mirrors fold() in skills/aor-signal/scripts/room_signal.py; the contract is
// skills/aor-signal/references/room-event-contract.md.
export const TRANSITIONS: Record<string, Decision[]> = {
  "ask:open": ["answered", "rejected"],
  "approval:open": ["approved", "edited", "rejected"],
  "approval:approved": ["done", "failed", "edited", "rejected"],
  "approval:edited": ["done", "failed", "edited", "rejected"],
};

export const OPERATOR_DECISIONS: Decision[] = ["answered", "approved", "edited", "rejected"];

export function allowedDecisions(item: Pick<Item, "kind" | "status">): Decision[] {
  return TRANSITIONS[`${item.kind}:${item.status}`] ?? [];
}

export const fireKey = (project: string | null, reason: unknown, ref: unknown) =>
  `${project}|${reason}|${ref ?? ""}`;
const riskKey = (project: string | null, risk: unknown) => `${project}|${risk}`;

export function sortEvents(events: RoomEvent[]): RoomEvent[] {
  return events
    .map((e, i) => [e, i] as const)
    .sort((a, b) => (a[0].ts < b[0].ts ? -1 : a[0].ts > b[0].ts ? 1 : a[1] - b[1]))
    .map(([e]) => e);
}

export function fold(events: RoomEvent[]): FoldedState {
  const agents: Record<string, AgentState> = {};
  const items: Record<string, Item> = {};
  const risks: Record<string, Risk> = {};
  const fires: Record<string, Fire> = {};
  const digested = new Set<string>();
  let lastDigest: string | null = null;
  const projects = new Set<string>();
  const early: Record<string, [Record<string, unknown>, string][]> = {};

  const applyResolve = (item: Item, d: Record<string, unknown>, ts: string) => {
    if (!allowedDecisions(item).includes(d.decision as Decision)) return;
    item.status = d.decision as Decision;
    item.resolved_at = ts;
    for (const k of ["answer", "payload", "by", "note", "result_url"] as const) {
      if (d[k] !== undefined && d[k] !== null) {
        (item as unknown as Record<string, unknown>)[k === "payload" ? "final_payload" : k] = d[k];
      }
    }
  };

  for (const e of events) {
    const { type: t, project: p, agent: a, ts } = e;
    const d = e.data ?? {};
    if (p) projects.add(p);
    if (t === "status") {
      agents[`${p}/${a}`] = { project: p!, agent: a!, updated_at: ts, ...(d as object) } as AgentState;
    } else if (t === "ask" || t === "approval") {
      items[e.id] = { id: e.id, kind: t, project: p!, owner: a!, created_at: ts, status: "open", ...(d as object) } as Item;
      for (const [rd, rts] of early[e.id] ?? []) applyResolve(items[e.id], rd, rts);
      delete early[e.id];
    } else if (t === "resolve") {
      const item = items[d.item as string];
      if (item) applyResolve(item, d, ts);
      else (early[d.item as string] ??= []).push([d, ts]);
    } else if (t === "risk_open") {
      risks[riskKey(p, d.risk)] = { risk: d.risk as string, project: p!, owner: a!, opened_at: ts, open: true, ...(d as object) } as Risk;
    } else if (t === "risk_close") {
      const k = riskKey(p, d.risk);
      if (risks[k]) Object.assign(risks[k], { open: false, closed_at: ts });
    } else if (t === "fire") {
      const key = fireKey(p, d.reason, d.ref);
      fires[key] = { key, project: p!, raised_by: a!, since: ts, active: true, ...(d as object) } as Fire;
    } else if (t === "fire_clear") {
      const key = fireKey(p, d.reason, d.ref);
      if (fires[key]) Object.assign(fires[key], { active: false, cleared_at: ts });
    } else if (t === "digest_sent") {
      const its = (d.items as string[] | undefined) ?? [];
      if (its.length) {
        its.forEach((i) => digested.add(i));
        lastDigest = ts;
      }
      for (const key of (d.fires as string[] | undefined) ?? []) {
        if (fires[key]?.active) fires[key].alerted_at = ts;
      }
    }
  }

  const health: Record<string, ProjectHealth> = {};
  for (const proj of [...projects].sort()) {
    const active = Object.values(fires).filter((f) => f.project === proj && f.active);
    const open = Object.values(items).filter((i) => i.project === proj && i.status === "open");
    health[proj] = {
      health: active.length ? "red" : open.length ? "amber" : "green",
      fires: active.map((f) => f.reason),
      needs_you: open.filter((i) => i.kind === "ask").length,
      approvals: open.filter((i) => i.kind === "approval").length,
    };
  }

  return { agents, items, risks, fires, projects: health, digested: [...digested].sort(), last_digest_at: lastDigest };
}
