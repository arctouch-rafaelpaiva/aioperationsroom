import type { RoomEvent } from "./types";

/**
 * Events pushed by agents (POST /api/events) and written by the room, kept until git
 * catches up. Uses Upstash Redis when configured (needed on Vercel, where instances
 * don't share memory), otherwise this process's memory.
 */
const KEY = "aor:events";
const MAX = 5000;

const memory: Map<string, RoomEvent> = ((globalThis as { __aorLive?: Map<string, RoomEvent> }).__aorLive ??= new Map());

function redis(): { url: string; token: string } | null {
  const url = process.env.KV_REST_API_URL ?? process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.KV_REST_API_TOKEN ?? process.env.UPSTASH_REDIS_REST_TOKEN;
  return url && token ? { url, token } : null;
}

async function command(args: (string | number)[]): Promise<unknown> {
  const r = redis()!;
  const res = await fetch(r.url, {
    method: "POST",
    cache: "no-store",
    headers: { Authorization: `Bearer ${r.token}`, "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });
  if (!res.ok) throw new Error(`Redis ${args[0]}: ${res.status}`);
  return ((await res.json()) as { result: unknown }).result;
}

export const liveBackend = () => (redis() ? "redis" : "memory");

export async function addLive(events: RoomEvent[]): Promise<number> {
  let added = 0;
  if (redis()) {
    for (const e of events) added += Number(await command(["HSETNX", KEY, e.id, JSON.stringify(e)]));
    return added;
  }
  for (const e of events) {
    if (!memory.has(e.id)) {
      memory.set(e.id, e);
      added++;
    }
  }
  while (memory.size > MAX) memory.delete(memory.keys().next().value!);
  return added;
}

export async function listLive(): Promise<RoomEvent[]> {
  if (redis()) {
    const flat = (await command(["HGETALL", KEY])) as string[];
    const out: RoomEvent[] = [];
    for (let i = 1; i < flat.length; i += 2) out.push(JSON.parse(flat[i]));
    return out;
  }
  return [...memory.values()];
}

/** Drops live copies that git already has, so the live store stays small. */
export async function pruneLive(inGit: Set<string>): Promise<void> {
  if (redis()) {
    const ids = ((await command(["HKEYS", KEY])) as string[]).filter((id) => inGit.has(id));
    if (ids.length) await command(["HDEL", KEY, ...ids]);
    return;
  }
  for (const id of inGit) memory.delete(id);
}
