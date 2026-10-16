"use client";

import { Hand, LayoutGrid, List, LogOut, MonitorPlay, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Toaster } from "@/components/ui/sonner";
import { useRoom, type Connection } from "@/hooks/use-room";
import { FIRE_LABEL, inQuietHours } from "@/lib/aor/describe";
import type { ResolveRequest } from "@/lib/aor/room";
import type { RoomSnapshot } from "@/lib/aor/types";
import { cn } from "@/lib/utils";
import { ApprovalsTray, ListView, MemberSheet, ProjectSheet } from "./panels";
import { RoomCanvas } from "./room-canvas";
import { SignIn } from "./sign-in";

const MODE_LABEL: Record<RoomSnapshot["mode"], string> = { demo: "Demo room", fs: "Local ops repo", github: "Ops repo on GitHub" };

const CONNECTION: Record<Connection, { dot: string; text: string }> = {
  connecting: { dot: "bg-zinc-400", text: "Connecting" },
  live: { dot: "bg-emerald-500", text: "Live" },
  retrying: { dot: "bg-amber-500 animate-pulse", text: "Reconnecting" },
  "signed-out": { dot: "bg-zinc-500", text: "Signed out" },
};

function useClock(timezone: string | undefined) {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    const tick = () => setNow(new Date());
    const first = setTimeout(tick, 0);
    const id = setInterval(tick, 15_000);
    return () => {
      clearTimeout(first);
      clearInterval(id);
    };
  }, []);
  if (!now || !timezone) return "";
  return new Intl.DateTimeFormat("en-GB", { timeZone: timezone, hour: "2-digit", minute: "2-digit", weekday: "short" }).format(now);
}

function beep() {
  try {
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "square";
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.6);
    osc.connect(gain).connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.6);
  } catch {
    // Browsers block audio until the screen has been clicked once.
  }
}

export function RoomApp({ kiosk, token, sound, passwordSet }: { kiosk: boolean; token: string | null; sound: boolean; passwordSet: boolean }) {
  const { snapshot, connection, error, refresh } = useRoom(token);
  const [view, setView] = useState<"room" | "list">(() =>
    !kiosk && typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches ? "list" : "room",
  );
  const [memberKey, setMemberKey] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [trayOpen, setTrayOpen] = useState(false);
  const [idle, setIdle] = useState(false);
  const clock = useClock(snapshot?.config.timezone);
  const seenFires = useRef<Set<string> | null>(null);

  useEffect(() => {
    if (!kiosk) return;
    let t: ReturnType<typeof setTimeout>;
    const wake = () => {
      setIdle(false);
      clearTimeout(t);
      t = setTimeout(() => setIdle(true), 3000);
    };
    wake();
    window.addEventListener("mousemove", wake);
    return () => {
      clearTimeout(t);
      window.removeEventListener("mousemove", wake);
    };
  }, [kiosk]);

  useEffect(() => {
    if (!snapshot) return;
    const keys = new Set(snapshot.projects.flatMap((p) => p.fires.map((f) => f.key)));
    if (seenFires.current && sound && [...keys].some((k) => !seenFires.current!.has(k))) beep();
    seenFires.current = keys;
  }, [snapshot, sound]);

  const resolve = useCallback(
    async (requests: ResolveRequest[]) => {
      const res = await fetch("/api/items/resolve", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ items: requests }) });
      const body = await res.json().catch(() => ({}));
      if (!res.ok && !body.results) {
        toast.error(body.error ?? "Couldn't record that decision");
        return false;
      }
      const results = (body.results ?? []) as { id: string; ok: boolean; error?: string }[];
      const okCount = results.filter((r) => r.ok).length;
      const failed = results.filter((r) => !r.ok);
      const verb = { approved: "Approved", edited: "Approved your edit", rejected: "Rejected", answered: "Answered" }[requests[0].decision as string] ?? "Done";
      if (okCount) toast.success(okCount > 1 ? `${verb} ${okCount} items` : `${verb}. The agent picks it up on its next run.`);
      for (const f of failed) toast.error(f.error ?? "Couldn't record that decision");
      await refresh();
      return okCount > 0;
    },
    [refresh],
  );

  const selection = useMemo(() => {
    if (!snapshot || !memberKey) return null;
    const [pid, aid] = memberKey.split("/");
    if (pid === "room") return { project: null, member: snapshot.maestro };
    const project = snapshot.projects.find((p) => p.id === pid);
    const member = project?.members.find((m) => m.id === aid);
    return project && member ? { project, member } : null;
  }, [snapshot, memberKey]);
  const project = snapshot?.projects.find((p) => p.id === projectId) ?? null;

  if (connection === "signed-out") return <SignIn message="Your session ended. Sign in again to keep watching the room." />;

  if (!snapshot) {
    return (
      <main className="flex min-h-dvh flex-col items-center justify-center gap-3 bg-[#11131b] p-6 text-center text-zinc-200">
        {error ? (
          <>
            <p className="text-lg font-semibold">The room is dark</p>
            <p className="max-w-md text-sm text-zinc-400">{error}</p>
            <Button variant="secondary" onClick={() => refresh()}>
              <RefreshCw /> Try again
            </Button>
          </>
        ) : (
          <>
            <div className="size-4 animate-bounce rounded-sm bg-amber-500" />
            <p className="text-sm text-zinc-400">Opening the room…</p>
          </>
        )}
      </main>
    );
  }

  const open = snapshot.items.filter((i) => i.status === "open");
  const approvals = open.filter((i) => i.kind === "approval").length;
  const asks = open.length - approvals;
  const fires = snapshot.projects.flatMap((p) => p.fires.map((f) => ({ ...f, projectName: p.name })));
  const night = inQuietHours(snapshot.config.quietHours, snapshot.config.timezone);
  const empty = snapshot.projects.length === 0;

  const room = (
    <div className="relative min-h-0 flex-1">
      {view === "room" || kiosk ? (
        <RoomCanvas
          snapshot={snapshot}
          night={kiosk && night}
          selectedKey={memberKey}
          onSelectMember={(k) => !kiosk && setMemberKey(k)}
          onSelectProject={(id) => !kiosk && setProjectId(id)}
        />
      ) : (
        <div className="h-full overflow-y-auto">
          <ListView snapshot={snapshot} onSelectMember={setMemberKey} onSelectProject={setProjectId} />
        </div>
      )}
      {empty && (
        <div className="pointer-events-none absolute inset-x-0 bottom-[18%] flex justify-center px-4">
          <div className="max-w-md rounded-xl border border-white/10 bg-zinc-950/90 p-4 text-center text-sm text-zinc-200 shadow-xl">
            <p className="font-semibold">No projects in the room yet</p>
            <p className="mt-1 text-zinc-400">Ask aor-onboard-project to “onboard project X”. Its pod and squad appear here as soon as the PM checks in.</p>
          </div>
        </div>
      )}
    </div>
  );

  if (kiosk) {
    const level = fires.length ? "red" : open.length ? "amber" : "green";
    return (
      <main className={cn("flex h-dvh flex-col bg-[#11131b] text-zinc-100", idle && "cursor-none")}>
        {room}
        <footer
          className={cn(
            "flex flex-wrap items-center gap-x-8 gap-y-2 px-6 py-4 text-2xl font-semibold",
            level === "red" ? "animate-pulse bg-red-600 text-white" : level === "amber" ? "bg-amber-500 text-black" : "bg-emerald-600 text-white",
          )}
        >
          {level === "red" &&
            fires.slice(0, 2).map((f) => (
              <span key={f.key}>
                🔥 {f.projectName}: {FIRE_LABEL[f.reason] ?? f.reason}
              </span>
            ))}
          {level !== "green" && (
            <span>
              {asks} need{asks === 1 ? "s" : ""} you · {approvals} to approve
            </span>
          )}
          {level === "green" && <span>All calm · the squads are working</span>}
          <span className="ml-auto text-lg font-medium opacity-80">
            {clock} {connection !== "live" && "· reconnecting…"}
          </span>
        </footer>
      </main>
    );
  }

  const conn = CONNECTION[connection];
  return (
    <main className="flex h-dvh flex-col bg-[#11131b] text-zinc-100">
      <header className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-white/10 bg-zinc-950 px-3 py-2 sm:px-4">
        <div className="flex items-center gap-2">
          <span className="grid size-6 place-items-center rounded bg-amber-500 text-sm text-black" aria-hidden>
            ◆
          </span>
          <h1 className="font-semibold">AI Operations Room</h1>
          <Badge variant="outline" className="hidden border-white/15 text-zinc-400 sm:inline-flex">
            {MODE_LABEL[snapshot.mode]}
          </Badge>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          {fires.length > 0 && <Badge className="bg-red-600 text-white">🔥 {fires.length} fire{fires.length > 1 ? "s" : ""}</Badge>}
          <Badge variant="outline" className={cn("border-white/15", asks ? "text-sky-300" : "text-zinc-500")}>
            ? {asks} need you
          </Badge>
          <Badge variant="outline" className={cn("border-white/15", approvals ? "text-amber-300" : "text-zinc-500")}>
            ✋ {approvals} to approve
          </Badge>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <span className="hidden items-center gap-1.5 text-xs text-zinc-400 md:flex" title={error ?? undefined}>
            <span className={cn("size-2 rounded-full", conn.dot)} /> {conn.text}
            {clock && ` · ${clock}`}
          </span>
          <div className="flex rounded-lg border border-white/10 p-0.5">
            <Button size="icon-sm" variant={view === "room" ? "secondary" : "ghost"} onClick={() => setView("room")} aria-label="Room view">
              <LayoutGrid />
            </Button>
            <Button size="icon-sm" variant={view === "list" ? "secondary" : "ghost"} onClick={() => setView("list")} aria-label="List view">
              <List />
            </Button>
          </div>
          <Button size="sm" className="bg-amber-500 text-black hover:bg-amber-400" onClick={() => setTrayOpen(true)}>
            <Hand /> <span className="hidden sm:inline">Waiting on you</span> {open.length}
          </Button>
          <Button size="icon-sm" variant="ghost" aria-label="Open kiosk view" title="Kiosk view for a wall screen" onClick={() => window.open("/?kiosk=1", "_blank")}>
            <MonitorPlay />
          </Button>
          {passwordSet && (
            <Button
              size="icon-sm"
              variant="ghost"
              aria-label="Sign out"
              onClick={async () => {
                await fetch("/api/session", { method: "DELETE" });
                window.location.reload();
              }}
            >
              <LogOut />
            </Button>
          )}
        </div>
      </header>
      {(snapshot.mode === "demo" || !snapshot.canAct || snapshot.warnings.length > 0) && (
        <div className="space-y-0.5 border-b border-white/10 bg-zinc-900 px-4 py-1.5 text-xs text-zinc-400">
          {snapshot.mode === "demo" && (
            <p>
              Demo room with sample projects; decisions stay in memory. Set <code className="text-zinc-300">AOR_OPS_DIR</code> or <code className="text-zinc-300">AOR_GITHUB_REPO</code> to connect your ops repo.
            </p>
          )}
          {!snapshot.canAct && <p>View only. Set AOR_OPERATOR_PASSWORD on the room and sign in to approve and answer.</p>}
          {snapshot.warnings.map((w) => (
            <p key={w}>{w}</p>
          ))}
        </div>
      )}
      {room}
      <MemberSheet snapshot={snapshot} selection={selection} onClose={() => setMemberKey(null)} onResolve={resolve} />
      <ProjectSheet
        snapshot={snapshot}
        project={project}
        onClose={() => setProjectId(null)}
        onResolve={resolve}
        onSelectMember={(k) => {
          setProjectId(null);
          setMemberKey(k);
        }}
      />
      <ApprovalsTray snapshot={snapshot} open={trayOpen} onOpenChange={setTrayOpen} onResolve={resolve} />
      <Toaster position="bottom-center" theme="dark" />
    </main>
  );
}
