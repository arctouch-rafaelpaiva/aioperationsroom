export interface RoleLook {
  name: string;
  title: string;
  icon: string;
  shirt: string;
  hair: string;
  skin: string;
}

// Default persona names match each skill's init-sanctum.py; a roster `name` overrides them.
export const ROLES: Record<string, RoleLook> = {
  maestro: { name: "Maestro", title: "Operations Room Conductor", icon: "🎼", shirt: "#1f2937", hair: "#e5e7eb", skin: "#f1c27d" },
  pm: { name: "Stella", title: "Project Stage Manager", icon: "🎧", shirt: "#7c3aed", hair: "#3b2416", skin: "#e0ac69" },
  discovery: { name: "Noor", title: "Discovery Specialist", icon: "🧭", shirt: "#0d9488", hair: "#111827", skin: "#c68642" },
  requirements: { name: "Ash", title: "Requirements and Backlog Specialist", icon: "📐", shirt: "#2563eb", hair: "#a16207", skin: "#f1c27d" },
  docs: { name: "Paige", title: "Documentation Specialist", icon: "📚", shirt: "#b45309", hair: "#7f1d1d", skin: "#ffdbac" },
  design: { name: "Iris", title: "Design Collaboration Specialist", icon: "🎨", shirt: "#db2777", hair: "#1e1b4b", skin: "#8d5524" },
  engineering: { name: "Theo", title: "Engineering Collaboration Specialist", icon: "🛠️", shirt: "#475569", hair: "#292524", skin: "#e0ac69" },
  qa: { name: "Vera", title: "QA and Acceptance Specialist", icon: "🔍", shirt: "#16a34a", hair: "#fbbf24", skin: "#ffdbac" },
  custom: { name: "Specialist", title: "Custom Specialist", icon: "✨", shirt: "#0891b2", hair: "#4b5563", skin: "#e0ac69" },
};

export const ROLE_ORDER = ["pm", "discovery", "requirements", "docs", "design", "engineering", "qa"];

export const MAESTRO_ID = "aor-agent-maestro";
export const ROOM_PROJECT = "room";

export function roleOf(agentId: string): string {
  const m = agentId.match(/^aor-agent-(.+)$/);
  return m && ROLES[m[1]] ? m[1] : "custom";
}

export function lookFor(role: string): RoleLook {
  return ROLES[role] ?? ROLES.custom;
}
