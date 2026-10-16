import { randomBytes, randomUUID } from "node:crypto";
import { EVENT_TYPES, type EventType, type RoomEvent } from "./types";

const PREFIX: Partial<Record<EventType, string>> = { ask: "q", approval: "ap" };

export function makeEvent(
  type: EventType,
  project: string | null,
  agent: string | null,
  data: Record<string, unknown>,
  run: string,
  now: Date = new Date(),
): RoomEvent {
  return {
    v: 1,
    id: `${PREFIX[type] ?? "ev"}-${randomBytes(6).toString("hex")}`,
    ts: now.toISOString(),
    type,
    project,
    agent,
    run,
    data,
  };
}

export const roomRunId = () => `room-${randomUUID()}`;

export function eventPath(runId: string, now: Date = new Date()): string {
  return `aor/room/events/${now.toISOString().slice(0, 10)}/${runId}.jsonl`;
}

export const toJsonl = (events: RoomEvent[]) => events.map((e) => JSON.stringify(e)).join("\n") + "\n";

export function parseJsonl(text: string): RoomEvent[] {
  const out: RoomEvent[] = [];
  for (const line of text.split("\n")) {
    if (!line.trim()) continue;
    try {
      const e = JSON.parse(line);
      if (!validateEvent(e)) out.push(e);
    } catch {
      // A half-written last line from a run in progress; git catches up on the next read.
    }
  }
  return out;
}

export function validateEvent(e: unknown): string | null {
  if (!e || typeof e !== "object") return "event must be an object";
  const ev = e as Record<string, unknown>;
  if (ev.v !== 1) return "v must be 1";
  if (typeof ev.id !== "string" || !ev.id) return "id is required";
  if (typeof ev.ts !== "string" || Number.isNaN(Date.parse(ev.ts))) return "ts must be an ISO-8601 timestamp";
  if (!EVENT_TYPES.includes(ev.type as EventType)) return `type must be one of ${EVENT_TYPES.join(", ")}`;
  if (ev.project !== null && typeof ev.project !== "string") return "project must be a string or null";
  if (ev.agent !== null && typeof ev.agent !== "string") return "agent must be a string or null";
  if (typeof ev.run !== "string") return "run is required";
  if (!ev.data || typeof ev.data !== "object" || Array.isArray(ev.data)) return "data must be an object";
  return null;
}
