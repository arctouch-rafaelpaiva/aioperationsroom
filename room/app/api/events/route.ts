import { bearerOk } from "@/lib/aor/auth";
import { validateEvent } from "@/lib/aor/events";
import { addLive } from "@/lib/aor/live";
import type { RoomEvent } from "@/lib/aor/types";

const MAX_EVENTS = 200;

/** Live push from aor-signal (room-event-contract.md). Git stays the source of truth. */
export async function POST(request: Request) {
  if (!process.env.AOR_ROOM_TOKEN) return Response.json({ error: "AOR_ROOM_TOKEN is not set on the room" }, { status: 503 });
  if (!bearerOk(request.headers.get("authorization"))) return Response.json({ error: "Bad or missing bearer token" }, { status: 401 });
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Body must be JSON: {\"events\": [...]}" }, { status: 400 });
  }
  const events = (body as { events?: unknown })?.events;
  if (!Array.isArray(events) || !events.length || events.length > MAX_EVENTS) {
    return Response.json({ error: `events must be a list of 1 to ${MAX_EVENTS} events` }, { status: 400 });
  }
  for (const [i, e] of events.entries()) {
    const problem = validateEvent(e);
    if (problem) return Response.json({ error: `events[${i}]: ${problem}` }, { status: 400 });
  }
  const added = await addLive(events as RoomEvent[]);
  return Response.json({ ok: true, added, duplicates: events.length - added }, { status: 202 });
}
