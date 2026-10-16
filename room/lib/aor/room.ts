import { makeEvent, roomRunId } from "./events";
import { allowedDecisions, fold, OPERATOR_DECISIONS, sortEvents } from "./fold";
import { addLive, listLive, pruneLive } from "./live";
import { lookFor, MAESTRO_ID, ROLE_ORDER, ROOM_PROJECT } from "./roster";
import { demoSource } from "./sources/demo";
import { fsSource } from "./sources/fs";
import { githubSource } from "./sources/github";
import type { OpsSource } from "./sources/types";
import type { AgentState, Decision, FoldedState, Item, Member, ProjectFile, RoomEvent, RoomSnapshot } from "./types";

const TIMELINE = 150;

export function getSource(): OpsSource {
  if (process.env.AOR_OPS_DIR) return fsSource(process.env.AOR_OPS_DIR);
  if (process.env.AOR_GITHUB_REPO && process.env.AOR_GITHUB_TOKEN) {
    return githubSource(process.env.AOR_GITHUB_REPO, process.env.AOR_GITHUB_TOKEN, process.env.AOR_GITHUB_BRANCH || "main");
  }
  return demoSource();
}

async function allEvents(source: OpsSource): Promise<RoomEvent[]> {
  const [git, live] = await Promise.all([source.listEvents(), listLive()]);
  const ids = new Set(git.map((e) => e.id));
  if (source.kind !== "demo") await pruneLive(new Set(live.filter((e) => ids.has(e.id)).map((e) => e.id)));
  return sortEvents([...git, ...live.filter((e) => !ids.has(e.id))]);
}

function member(id: string, role: string, name: string | undefined, agent: AgentState | undefined, items: Item[]): Member {
  const look = lookFor(role);
  const mine = items.filter((i) => i.owner === id && i.status === "open");
  return {
    id,
    role,
    name: name ?? look.name,
    title: look.title,
    icon: look.icon,
    status: agent?.status ?? "offline",
    task: agent?.task,
    source_url: agent?.source_url,
    updated_at: agent?.updated_at,
    approvals: mine.filter((i) => i.kind === "approval").length,
    asks: mine.filter((i) => i.kind === "ask").length,
  };
}

function rosterOrder(a: ProjectFile["roster"][number], b: ProjectFile["roster"][number]) {
  const rank = (r: string) => (ROLE_ORDER.includes(r) ? ROLE_ORDER.indexOf(r) : ROLE_ORDER.length);
  return rank(a.role) - rank(b.role);
}

export function buildSnapshot(
  source: OpsSource["kind"],
  state: FoldedState,
  events: RoomEvent[],
  projects: ProjectFile[],
  config: RoomSnapshot["config"],
  canAct: boolean,
): RoomSnapshot {
  const items = Object.values(state.items);
  const active = projects.filter((p) => p.status === "active");
  const known = new Set(active.map((p) => p.id));
  const warnings: string[] = [];
  const orphan = Object.keys(state.projects).filter((p) => p !== ROOM_PROJECT && !known.has(p) && !projects.some((x) => x.id === p));
  if (orphan.length) warnings.push(`Events for projects without a project.yaml: ${orphan.join(", ")}`);

  return {
    mode: source,
    generatedAt: new Date().toISOString(),
    config,
    canAct,
    warnings,
    maestro: member(MAESTRO_ID, "maestro", undefined, state.agents[`${ROOM_PROJECT}/${MAESTRO_ID}`], items.filter((i) => i.project === ROOM_PROJECT)),
    projects: active.map((p) => {
      const h = state.projects[p.id];
      const projectItems = items.filter((i) => i.project === p.id);
      return {
        id: p.id,
        name: p.name,
        health: h?.health ?? "green",
        needs_you: h?.needs_you ?? 0,
        approvals: h?.approvals ?? 0,
        fires: Object.values(state.fires).filter((f) => f.project === p.id && f.active),
        risks: Object.values(state.risks).filter((r) => r.project === p.id && r.open),
        members: [...p.roster].sort(rosterOrder).map((r) => member(r.id, r.role, r.name, state.agents[`${p.id}/${r.id}`], projectItems)),
      };
    }),
    items: items
      .filter((i) => i.project === ROOM_PROJECT || known.has(i.project))
      .sort((a, b) => (a.created_at < b.created_at ? 1 : -1)),
    timeline: events.filter((e) => e.type !== "digest_sent").slice(-TIMELINE).reverse(),
  };
}

export async function getSnapshot(canAct: boolean): Promise<RoomSnapshot> {
  const source = getSource();
  const [events, projects, config] = await Promise.all([allEvents(source), source.listProjects(), source.config()]);
  return buildSnapshot(source.kind, fold(events), events, projects, config, canAct);
}

export interface ResolveRequest {
  id: string;
  decision: Decision;
  answer?: string;
  payload?: unknown;
  note?: string;
}

export interface ResolveResult {
  id: string;
  ok: boolean;
  error?: string;
}

export function planResolves(state: FoldedState, requests: ResolveRequest[], by: string, run: string) {
  const results: ResolveResult[] = [];
  const events: RoomEvent[] = [];
  for (const r of requests) {
    const item = state.items[r.id];
    if (!item) {
      results.push({ id: r.id, ok: false, error: "No such item" });
      continue;
    }
    if (!OPERATOR_DECISIONS.includes(r.decision) || !allowedDecisions(item).includes(r.decision)) {
      results.push({ id: r.id, ok: false, error: `Can't ${r.decision} an item that is ${item.status}` });
      continue;
    }
    if (r.decision === "edited" && (r.payload === undefined || r.payload === "")) {
      results.push({ id: r.id, ok: false, error: "An edit needs the new content" });
      continue;
    }
    if (r.decision === "answered" && !r.answer?.trim()) {
      results.push({ id: r.id, ok: false, error: "An answer can't be empty" });
      continue;
    }
    const data: Record<string, unknown> = { item: r.id, decision: r.decision, by };
    if (r.answer) data.answer = r.answer.trim();
    if (r.decision === "edited") data.payload = r.payload;
    if (r.note?.trim()) data.note = r.note.trim();
    events.push(makeEvent("resolve", item.project, "room", data, run));
    results.push({ id: r.id, ok: true });
    item.status = r.decision;
  }
  return { events, results };
}

export async function resolveItems(requests: ResolveRequest[], by: string): Promise<ResolveResult[]> {
  const source = getSource();
  const state = fold(await allEvents(source));
  const run = roomRunId();
  const { events, results } = planResolves(state, requests, by, run);
  if (events.length) {
    await source.append(events, run);
    if (source.kind !== "demo") await addLive(events);
  }
  return results;
}
