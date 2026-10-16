import type { ProjectFile, RoomConfig, RoomEvent, SourceKind } from "../types";

export interface OpsSource {
  kind: SourceKind;
  listEvents(): Promise<RoomEvent[]>;
  listProjects(): Promise<ProjectFile[]>;
  config(): Promise<RoomConfig>;
  /** Writes one new event file, as the contract asks of the room's own writes. */
  append(events: RoomEvent[], runId: string): Promise<void>;
}

export const DEFAULT_CONFIG: RoomConfig = { timezone: "America/Sao_Paulo", quietHours: "19:00-07:30" };

export function configFromYaml(doc: unknown): RoomConfig {
  const aor = (doc && typeof doc === "object" ? (doc as Record<string, unknown>).aor : null) as Record<string, unknown> | null;
  return {
    timezone: typeof aor?.aor_timezone === "string" ? aor.aor_timezone : DEFAULT_CONFIG.timezone,
    quietHours: typeof aor?.aor_quiet_hours === "string" ? aor.aor_quiet_hours : DEFAULT_CONFIG.quietHours,
  };
}

export function projectFromYaml(doc: unknown): ProjectFile | null {
  if (!doc || typeof doc !== "object") return null;
  const p = doc as Record<string, unknown>;
  if (typeof p.id !== "string" || !Array.isArray(p.roster)) return null;
  return {
    id: p.id,
    name: typeof p.name === "string" ? p.name : p.id,
    status: p.status === "archived" ? "archived" : "active",
    roster: p.roster
      .filter((r): r is Record<string, unknown> => !!r && typeof r === "object" && typeof (r as { id?: unknown }).id === "string")
      .map((r) => ({
        id: r.id as string,
        role: typeof r.role === "string" ? r.role : "custom",
        skill: typeof r.skill === "string" ? r.skill : undefined,
        name: typeof r.name === "string" ? r.name : undefined,
      })),
  };
}
