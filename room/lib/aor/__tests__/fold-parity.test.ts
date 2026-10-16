import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterAll, describe, expect, it } from "vitest";
import { makeEvent } from "../events";
import { fold, sortEvents } from "../fold";
import { planResolves } from "../room";
import { fsSource } from "../sources/fs";

const SCRIPT = path.resolve(__dirname, "../../../../skills/aor-signal/scripts/room_signal.py");
const root = mkdtempSync(path.join(tmpdir(), "aor-parity-"));
afterAll(() => rmSync(root, { recursive: true, force: true }));

let clock = Date.parse("2026-10-16T12:00:00.000Z");
function signal(...args: string[]): Record<string, unknown> {
  clock += 1000;
  const out = execFileSync("python3", ["-B", SCRIPT, "--root", root, "--no-push", "--now", new Date(clock).toISOString(), ...args], {
    env: { ...process.env, AOR_RUN_ID: "parity-run", AOR_ROOM_URL: "" },
    encoding: "utf8",
  });
  return JSON.parse(out);
}

describe("fold matches aor-signal's fold", () => {
  it("agrees on every section after agent and room writes", async () => {
    const who = ["--project", "acme", "--agent", "aor-agent-qa"];
    signal("status", ...who, "--status", "drafting", "--task", "Writing scenarios");
    const ask = signal("ask", ...who, "--question", "Which browsers?", "--options", "Chrome|All").events as string[];
    const ap = signal("approval", ...who, "--target", "github", "--action", "comment", "--preview", "Coverage", "--rationale", "AC3 untested", "--payload", "AC3 has no test").events as string[];
    const ap2 = signal("approval", ...who, "--target", "jira", "--action", "comment", "--preview", "Severity", "--rationale", "Triage", "--payload", "{\"sev\": 2}").events as string[];
    signal("fire", "--project", "acme", "--agent", "aor-agent-pm", "--reason", "failed_build", "--detail", "CI red", "--ref", "pr-1");
    signal("fire", "--project", "acme", "--agent", "aor-agent-pm", "--reason", "other", "--detail", "Client upset");
    signal("fire", "--project", "acme", "--agent", "aor-agent-pm", "--reason", "other", "--clear");
    signal("risk", "open", "--project", "acme", "--agent", "aor-agent-engineering", "--risk", "sdk", "--title", "SDK bump");
    signal("risk", "open", "--project", "beta", "--agent", "aor-agent-engineering", "--risk", "sdk", "--title", "Same id, other project");
    signal("risk", "close", "--project", "beta", "--agent", "aor-agent-engineering", "--risk", "sdk");

    const source = fsSource(root);
    const before = fold(sortEvents(await source.listEvents()));
    const { events, results } = planResolves(
      before,
      [
        { id: ap[0], decision: "approved" },
        { id: ap2[0], decision: "edited", payload: { sev: 3 } },
        { id: ask[0], decision: "approved" },
        { id: "q-missing", decision: "answered", answer: "x" },
      ],
      "operator",
      "room-test",
    );
    expect(results.map((r) => r.ok)).toEqual([true, true, false, false]);
    await source.append(events, "room-test");
    clock = Date.now() + 5000;
    signal("resolve", "--item", ap[0], "--decision", "done", "--by", "aor-agent-qa", "--result-url", "https://x/1");
    signal("resolve", "--item", ask[0], "--decision", "answered", "--by", "operator", "--answer", "All");

    const ours = fold(sortEvents(await source.listEvents()));
    const theirs = signal("state");
    delete theirs.ok;
    expect(JSON.parse(JSON.stringify(ours))).toEqual(theirs);
    expect(ours.items[ap[0]].status).toBe("done");
    expect(ours.items[ap2[0]]).toMatchObject({ status: "edited", final_payload: { sev: 3 } });
    expect(ours.projects.acme).toMatchObject({ health: "red", approvals: 0, needs_you: 0, fires: ["failed_build"] });
  });

  it("holds a resolve that sorts before its item", () => {
    const item = makeEvent("ask", "p", "aor-agent-pm", { question: "?" }, "r1", new Date("2026-10-16T10:00:00.000Z"));
    const res = makeEvent("resolve", "p", "room", { item: item.id, decision: "answered", answer: "yes", by: "operator" }, "r2", new Date("2026-10-16T10:00:00.000Z"));
    expect(fold([res, item]).items[item.id]).toMatchObject({ status: "answered", answer: "yes" });
  });

  it("checks each decision in a batch against the ones before it", () => {
    const item = makeEvent("ask", "p", "aor-agent-pm", { question: "?" }, "r1", new Date("2026-10-16T10:00:00.000Z"));
    const { results } = planResolves(fold([item]), [
      { id: item.id, decision: "answered", answer: "yes" },
      { id: item.id, decision: "answered", answer: "again" },
    ], "operator", "room-x");
    expect(results.map((r) => r.ok)).toEqual([true, false]);
  });

  it("ignores illegal transitions", () => {
    const item = makeEvent("ask", "p", "aor-agent-pm", { question: "?" }, "r1", new Date("2026-10-16T10:00:00.000Z"));
    const bad = makeEvent("resolve", "p", "room", { item: item.id, decision: "done" }, "r2", new Date("2026-10-16T10:00:01.000Z"));
    expect(fold([item, bad]).items[item.id].status).toBe("open");
  });
});
