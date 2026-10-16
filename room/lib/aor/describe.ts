import { lookFor, MAESTRO_ID, roleOf } from "./roster";
import type { Item, RoomEvent, RoomSnapshot } from "./types";

export const TARGET_LABEL: Record<string, string> = { jira: "Jira", notion: "Notion", github: "GitHub", figma: "Figma", slack: "Slack" };

export const STATUS_LABEL: Record<string, string> = {
  idle: "Idle",
  working: "Working",
  reading: "Reading",
  drafting: "Drafting",
  meeting: "In a meeting",
  wrapping: "Wrapping up",
  offline: "Away",
};

export const FIRE_LABEL: Record<string, string> = {
  failed_build: "Failed build",
  missed_deadline: "Missed deadline",
  client_escalation: "Client escalation",
  blocker_overdue: "Blocker overdue",
  other: "Fire",
};

export function memberName(snap: RoomSnapshot, project: string | null, agent: string | null): string {
  if (!agent) return "Someone";
  if (agent === MAESTRO_ID) return "Maestro";
  if (agent === "room" || agent === "operator") return "You";
  if (agent === "slack") return "You (Slack)";
  const m = snap.projects.find((p) => p.id === project)?.members.find((x) => x.id === agent);
  return m?.name ?? lookFor(roleOf(agent)).name;
}

export function projectName(snap: RoomSnapshot, id: string | null): string {
  if (!id || id === "room") return "Room";
  return snap.projects.find((p) => p.id === id)?.name ?? id;
}

const DECISION_TEXT: Record<string, string> = {
  answered: "answered",
  approved: "approved",
  edited: "edited and approved",
  rejected: "rejected",
  done: "posted",
  failed: "couldn't post",
};

export function itemTitle(item: Item): string {
  if (item.kind === "ask") return item.question ?? "A question";
  return item.preview ?? `${TARGET_LABEL[item.target ?? ""] ?? item.target} ${item.action ?? "post"}`;
}

export function describeEvent(snap: RoomSnapshot, e: RoomEvent): string {
  const who = memberName(snap, e.project, e.agent);
  const d = e.data as Record<string, string | undefined>;
  switch (e.type) {
    case "status":
      return d.task ? `${who}: ${d.task}` : `${who} is ${STATUS_LABEL[d.status ?? ""]?.toLowerCase() ?? d.status}`;
    case "ask":
      return `${who} asked: ${d.question}`;
    case "approval":
      return `${who} raised a hand: ${d.preview}`;
    case "resolve": {
      const item = snap.items.find((i) => i.id === d.item);
      return `${who} ${DECISION_TEXT[d.decision ?? ""] ?? d.decision} ${item ? `“${itemTitle(item)}”` : d.item}`;
    }
    case "risk_open":
      return `${who} flagged a ${d.kind ?? "risk"}: ${d.title ?? d.risk}`;
    case "risk_close":
      return `${who} closed risk ${d.risk}`;
    case "fire":
      return `🔥 ${FIRE_LABEL[d.reason ?? ""] ?? "Fire"}: ${d.detail ?? d.ref ?? ""}`;
    case "fire_clear":
      return `${FIRE_LABEL[d.reason ?? ""] ?? "Fire"} cleared`;
    default:
      return e.type;
  }
}

export function timeAgo(iso: string | undefined, now = Date.now()): string {
  if (!iso) return "";
  const s = Math.max(0, Math.round((now - Date.parse(iso)) / 1000));
  if (s < 45) return "just now";
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} h ago`;
  return `${Math.round(h / 24)} d ago`;
}

export function inQuietHours(range: string, timezone: string, now = new Date()): boolean {
  const m = range.match(/^(\d{2}):(\d{2})-(\d{2}):(\d{2})$/);
  if (!m) return false;
  const parts = new Intl.DateTimeFormat("en-GB", { timeZone: timezone, hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(now);
  const minute = Number(parts.find((p) => p.type === "hour")?.value) * 60 + Number(parts.find((p) => p.type === "minute")?.value);
  const start = Number(m[1]) * 60 + Number(m[2]);
  const end = Number(m[3]) * 60 + Number(m[4]);
  return start <= end ? minute >= start && minute < end : minute >= start || minute < end;
}

export function payloadText(payload: unknown): string {
  if (payload === undefined || payload === null) return "";
  return typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
}
