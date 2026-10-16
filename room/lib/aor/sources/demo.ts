import { makeEvent } from "../events";
import { MAESTRO_ID, ROOM_PROJECT } from "../roster";
import type { AgentStatus, ProjectFile, RoomEvent } from "../types";
import { DEFAULT_CONFIG, type OpsSource } from "./types";

const squad = (roles: string[]) => roles.map((role) => ({ id: `aor-agent-${role}`, role, skill: `aor-agent-${role}` }));
const ALL = ["pm", "discovery", "requirements", "docs", "design", "engineering", "qa"];

const PROJECTS: ProjectFile[] = [
  { id: "checkout-revamp", name: "Checkout Revamp", status: "active", roster: squad(ALL) },
  { id: "partner-portal", name: "Partner Portal", status: "active", roster: squad(ALL) },
  {
    id: "mobile-onboarding",
    name: "Mobile Onboarding",
    status: "active",
    roster: [
      ...squad(["pm", "requirements", "design", "engineering", "qa"]),
      { id: "aor-custom-localization", role: "custom", skill: "aor-agent-docs", name: "Lio" },
    ],
  },
];

const TASKS: Record<string, [AgentStatus, string][]> = {
  pm: [
    ["working", "Triaging 3 new inbox items"],
    ["working", "Routing PR #482 to Theo and Vera"],
    ["drafting", "Drafting the weekly stakeholder update"],
    ["reading", "Reading yesterday's wrap before the stand-up"],
  ],
  discovery: [
    ["reading", "Synthesizing 14 new feedback notes from support"],
    ["working", "Ranking themes: saved cards is now a strong theme"],
    ["drafting", "Writing an opportunity brief for guest checkout"],
  ],
  requirements: [
    ["reading", "Checking 6 stories against the Definition of Ready"],
    ["drafting", "Drafting stories for the saved-cards epic"],
    ["drafting", "Preparing Thursday's refinement agenda"],
  ],
  docs: [
    ["drafting", "Logging the decision to drop PayPal from v1"],
    ["reading", "Checking the PRD against 3 new decisions"],
    ["drafting", "Drafting release notes for 2.14"],
  ],
  design: [
    ["reading", "Reviewing empty and error states on the cart frames"],
    ["reading", "Walking the sign-up flow for dead ends"],
    ["working", "Mapping sprint 23 stories to frames"],
  ],
  engineering: [
    ["reading", "Reading PR #482: payment SDK upgrade"],
    ["working", "Diffing dependencies: payment-sdk 4.2 → 5.0 (major)"],
    ["drafting", "Writing the change digest for yesterday's merges"],
  ],
  qa: [
    ["reading", "Tracing acceptance criteria to tests on PR #479"],
    ["drafting", "Writing scenarios for CHK-212 saved cards"],
    ["working", "Triaging BUG-77: double charge on retry"],
  ],
  custom: [
    ["reading", "Checking new strings against the pt-BR glossary"],
    ["drafting", "Drafting translations for the welcome carousel"],
  ],
};

const MAESTRO_TASKS: [AgentStatus, string][] = [
  ["reading", "Watching the portfolio for fires"],
  ["working", "Taking in client email and Slack"],
  ["idle", "Waiting for the next relay"],
];

const NEW_ITEMS: { kind: "ask" | "approval"; project: string; agent: string; data: Record<string, unknown> }[] = [
  {
    kind: "ask",
    project: "mobile-onboarding",
    agent: "aor-agent-design",
    data: { question: "Should the skip button appear on the first onboarding screen, or only from the second?", options: ["First screen", "From the second"] },
  },
  {
    kind: "approval",
    project: "mobile-onboarding",
    agent: "aor-agent-engineering",
    data: {
      target: "github",
      action: "pr_comment",
      payload: "The welcome carousel reads copy from a hard-coded array. ONB-31 asks for remote config so marketing can change it without a release. Is that planned for a follow-up?",
      preview: "Comment on PR #91: the carousel copy is hard-coded, but ONB-31 asks for remote config.",
      rationale: "Gap between the change and its story's acceptance criteria.",
      target_url: "https://github.com/acme/mobile/pull/91",
    },
  },
  {
    kind: "approval",
    project: "checkout-revamp",
    agent: "aor-agent-docs",
    data: {
      target: "notion",
      action: "page_update",
      payload: "Payment methods (v1): cards and Pix. PayPal moved to v1.1 (decision 2026-10-14, owner: Dana).",
      preview: "Update 'Checkout PRD → Payment methods' to drop PayPal from v1.",
      rationale: "Decision logged on 10-14 contradicts the PRD.",
    },
  },
];

interface DemoStore {
  events: RoomEvent[];
  lastTick: number;
  nextItem: number;
}

function ago(now: number, minutes: number) {
  return new Date(now - minutes * 60_000);
}

function seed(now: number): RoomEvent[] {
  const ev = (type: RoomEvent["type"], project: string, agent: string, data: Record<string, unknown>, min: number, id?: string) => {
    const e = makeEvent(type, project, agent, data, "demo-seed", ago(now, min));
    return id ? { ...e, id } : e;
  };
  const out: RoomEvent[] = [ev("status", ROOM_PROJECT, MAESTRO_ID, { status: "reading", task: "Watching the portfolio for fires" }, 3)];
  for (const p of PROJECTS) {
    p.roster.forEach((r, i) => {
      const pool = TASKS[r.role] ?? TASKS.custom;
      const [status, task] = pool[i % pool.length];
      out.push(ev("status", p.id, r.id, { status, task }, 40 - i * 3));
    });
  }
  out.push(
    ev("fire", "checkout-revamp", "aor-agent-pm", {
      reason: "failed_build",
      detail: "CI is failing on main since PR #482 bumped payment-sdk to 5.0",
      ref: "github:acme/checkout#482",
    }, 25),
    ev("risk_open", "checkout-revamp", "aor-agent-engineering", {
      risk: "payment-sdk-5",
      title: "payment-sdk 5.0 removes the legacy tokenize() call that saved cards use",
      kind: "blocker",
      severity: "high",
      ref: "CHK-212",
    }, 30),
    ev("approval", "checkout-revamp", "aor-agent-engineering", {
      target: "github",
      action: "pr_comment",
      payload: "payment-sdk 5.0 removes tokenize(), which CHK-212 (saved cards) relies on. Suggest pinning 4.x on main until the migration story is ready, and opening CHK-230 for the 5.0 migration.",
      preview: "Comment on PR #482: suggest pinning payment-sdk 4.x until saved cards migrate.",
      rationale: "Major bump breaks a story in the current sprint; CI is red on main.",
      target_url: "https://github.com/acme/checkout/pull/482",
    }, 18, "ap-demo-pin-sdk"),
    ev("approval", "partner-portal", "aor-agent-requirements", {
      target: "jira",
      action: "create_issues",
      payload: { epic: "PP-40 Partner SSO", stories: ["PP-41 Sign in with Okta", "PP-42 Sign in with Azure AD", "PP-43 Just-in-time provisioning", "PP-44 SSO audit log"] },
      preview: "Create 4 stories under the Partner SSO epic (PP-40), each with acceptance criteria.",
      rationale: "Opportunity brief approved on Tuesday; refinement is Thursday.",
    }, 50, "ap-demo-sso-stories"),
    ev("approval", "partner-portal", "aor-agent-qa", {
      target: "github",
      action: "pr_comment",
      payload: "Coverage check for PR #311 against PP-37: AC1 and AC2 are covered by tests; AC3 (expired invite links show a clear error) has no test. Suggested: an e2e test that opens a 48-hour-old invite.",
      preview: "Comment on PR #311: AC3 of PP-37 has no test.",
      rationale: "One acceptance criterion is untested.",
      target_url: "https://github.com/acme/portal/pull/311",
    }, 12, "ap-demo-coverage"),
    ev("ask", "partner-portal", "aor-agent-pm", {
      question: "The client asked to move the SSO launch to November 3. Do we accept the new date, or hold the original November 17?",
      options: ["Accept November 3", "Hold November 17"],
    }, 35, "q-demo-sso-date"),
  );
  return out;
}

function store(): DemoStore {
  const g = globalThis as { __aorDemo?: DemoStore };
  if (!g.__aorDemo) {
    const now = Date.now();
    g.__aorDemo = { events: seed(now), lastTick: now, nextItem: 0 };
  }
  return g.__aorDemo;
}

const pick = <T,>(xs: T[]) => xs[Math.floor(Math.random() * xs.length)];

/** Moves the demo forward: agents change tasks, a pod holds a stand-up, approved posts get posted. */
function tick(s: DemoStore, now: number) {
  if (now - s.lastTick < 5000) return;
  const elapsed = now - s.lastTick;
  s.lastTick = now;
  const add = (e: RoomEvent) => s.events.push(e);
  const at = new Date(now);

  for (let n = 0; n < Math.min(3, Math.ceil(elapsed / 5000)); n++) {
    const p = pick(PROJECTS);
    const r = pick(p.roster);
    const roll = Math.random();
    const [status, task]: [AgentStatus, string] =
      roll < 0.08 ? ["idle", "Waiting for the next cue"] : roll < 0.12 ? ["wrapping", "Filing today's session notes"] : pick(TASKS[r.role] ?? TASKS.custom);
    add(makeEvent("status", p.id, r.id, { status, task }, "demo-run", at));
  }

  if (Math.random() < 0.12) {
    const p = pick(PROJECTS);
    for (const r of p.roster) add(makeEvent("status", p.id, r.id, { status: "meeting", task: "Stand-up at the pod table" }, "demo-run", at));
  }
  if (Math.random() < 0.3) {
    const [status, task] = pick(MAESTRO_TASKS);
    add(makeEvent("status", ROOM_PROJECT, MAESTRO_ID, { status, task }, "demo-run", at));
  }

  // Approved and edited items get posted by their owner a few seconds later.
  const posted = new Set(s.events.filter((e) => e.type === "resolve" && ["done", "failed"].includes(e.data.decision as string)).map((e) => e.data.item));
  for (const e of s.events) {
    if (e.type !== "resolve" || !["approved", "edited"].includes(e.data.decision as string) || posted.has(e.data.item)) continue;
    if (now - Date.parse(e.ts) < 6000) continue;
    const item = s.events.find((x) => x.id === e.data.item);
    if (!item) continue;
    posted.add(e.data.item);
    add(makeEvent("resolve", item.project, item.agent, { item: item.id, decision: "done", by: item.agent, result_url: item.data.target_url }, "demo-run", at));
    add(makeEvent("status", item.project, item.agent, { status: "working", task: `Posted the approved ${String(item.data.target)} ${String(item.data.action).replace("_", " ")}` }, "demo-run", at));
  }

  const open = s.events.filter((e) => (e.type === "ask" || e.type === "approval") && !s.events.some((r) => r.type === "resolve" && r.data.item === e.id));
  if (open.length < 3 && s.nextItem < NEW_ITEMS.length && Math.random() < 0.25) {
    const it = NEW_ITEMS[s.nextItem++];
    add(makeEvent(it.kind, it.project, it.agent, it.data, "demo-run", at));
  }
}

export function demoSource(): OpsSource {
  return {
    kind: "demo",
    async listEvents() {
      const s = store();
      tick(s, Date.now());
      return [...s.events];
    },
    async listProjects() {
      return PROJECTS;
    },
    async config() {
      return DEFAULT_CONFIG;
    },
    async append(events) {
      store().events.push(...events);
    },
  };
}
