export const STATUSES = ["idle", "working", "reading", "drafting", "meeting", "wrapping", "offline"] as const;
export type AgentStatus = (typeof STATUSES)[number];

export const EVENT_TYPES = [
  "status",
  "ask",
  "approval",
  "resolve",
  "risk_open",
  "risk_close",
  "fire",
  "fire_clear",
  "digest_sent",
] as const;
export type EventType = (typeof EVENT_TYPES)[number];

export const TARGETS = ["jira", "notion", "github", "figma", "slack"] as const;
export type Target = (typeof TARGETS)[number];

export type Decision = "answered" | "approved" | "edited" | "rejected" | "done" | "failed";
export type ItemStatus = "open" | Decision;

export interface RoomEvent {
  v: number;
  id: string;
  ts: string;
  type: EventType;
  project: string | null;
  agent: string | null;
  run: string;
  data: Record<string, unknown>;
}

export interface AgentState {
  project: string;
  agent: string;
  status: AgentStatus;
  task?: string;
  source_url?: string;
  updated_at: string;
}

export interface Item {
  id: string;
  kind: "ask" | "approval";
  project: string;
  owner: string;
  created_at: string;
  status: ItemStatus;
  resolved_at?: string;
  question?: string;
  options?: string[];
  context_url?: string;
  target?: Target;
  action?: string;
  payload?: unknown;
  preview?: string;
  rationale?: string;
  target_url?: string;
  answer?: string;
  final_payload?: unknown;
  by?: string;
  note?: string;
  result_url?: string;
}

export interface Risk {
  risk: string;
  project: string;
  owner: string;
  title?: string;
  kind?: "blocker" | "risk";
  severity?: string;
  ref?: string;
  opened_at: string;
  closed_at?: string;
  open: boolean;
}

export interface Fire {
  key: string;
  project: string;
  raised_by: string;
  reason: string;
  detail?: string;
  ref?: string;
  since: string;
  active: boolean;
  cleared_at?: string;
  alerted_at?: string;
}

export type Health = "green" | "amber" | "red";

export interface ProjectHealth {
  health: Health;
  fires: string[];
  needs_you: number;
  approvals: number;
}

export interface FoldedState {
  agents: Record<string, AgentState>;
  items: Record<string, Item>;
  risks: Record<string, Risk>;
  fires: Record<string, Fire>;
  projects: Record<string, ProjectHealth>;
  digested: string[];
  last_digest_at: string | null;
}

export interface RosterEntry {
  id: string;
  role: string;
  skill?: string;
  name?: string;
}

export interface ProjectFile {
  id: string;
  name: string;
  status: "active" | "archived";
  roster: RosterEntry[];
}

export interface RoomConfig {
  timezone: string;
  quietHours: string;
}

export interface Member {
  id: string;
  role: string;
  name: string;
  title: string;
  icon: string;
  status: AgentStatus;
  task?: string;
  source_url?: string;
  updated_at?: string;
  approvals: number;
  asks: number;
}

export interface ProjectView {
  id: string;
  name: string;
  health: Health;
  fires: Fire[];
  risks: Risk[];
  needs_you: number;
  approvals: number;
  members: Member[];
}

export type SourceKind = "demo" | "fs" | "github";

export interface RoomSnapshot {
  mode: SourceKind;
  generatedAt: string;
  config: RoomConfig;
  maestro: Member;
  projects: ProjectView[];
  items: Item[];
  timeline: RoomEvent[];
  canAct: boolean;
  warnings: string[];
}
