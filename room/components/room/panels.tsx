"use client";

import { ExternalLink } from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { describeEvent, FIRE_LABEL, STATUS_LABEL, timeAgo } from "@/lib/aor/describe";
import type { ResolveRequest } from "@/lib/aor/room";
import { ROOM_PROJECT } from "@/lib/aor/roster";
import type { Health, Member, ProjectView, RoomEvent, RoomSnapshot } from "@/lib/aor/types";
import { cn } from "@/lib/utils";
import { ItemCard } from "./item-card";

export const HEALTH_DOT: Record<Health, string> = { green: "bg-emerald-500", amber: "bg-amber-500", red: "bg-red-500 animate-pulse" };
const HEALTH_TEXT: Record<Health, string> = { green: "All calm", amber: "Needs you", red: "On fire" };

type Resolve = (requests: ResolveRequest[]) => Promise<boolean>;

export function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "offline"
      ? "text-muted-foreground"
      : status === "meeting"
        ? "border-violet-500/50 text-violet-600 dark:text-violet-300"
        : status === "idle"
          ? "text-muted-foreground"
          : "border-emerald-500/50 text-emerald-700 dark:text-emerald-300";
  return (
    <Badge variant="outline" className={tone}>
      {STATUS_LABEL[status] ?? status}
    </Badge>
  );
}

function Timeline({ snapshot, events, empty }: { snapshot: RoomSnapshot; events: RoomEvent[]; empty: string }) {
  if (!events.length) return <p className="text-sm text-muted-foreground">{empty}</p>;
  return (
    <ol className="space-y-2.5">
      {events.slice(0, 40).map((e) => (
        <li key={e.id} className="flex gap-2 text-sm">
          <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-muted-foreground/50" />
          <div className="min-w-0">
            <p className="leading-snug">{describeEvent(snapshot, e)}</p>
            <p className="text-xs text-muted-foreground">{timeAgo(e.ts)}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function MemberSheet({
  snapshot,
  selection,
  onClose,
  onResolve,
}: {
  snapshot: RoomSnapshot;
  selection: { project: ProjectView | null; member: Member } | null;
  onClose: () => void;
  onResolve: Resolve;
}) {
  const projectId = selection?.project?.id ?? ROOM_PROJECT;
  const m = selection?.member;
  const items = snapshot.items.filter((i) => m && i.owner === m.id && i.project === projectId);
  const open = items.filter((i) => i.status === "open" || i.status === "approved" || i.status === "edited");
  const events = snapshot.timeline.filter((e) => m && e.agent === m.id && e.project === projectId);
  return (
    <Sheet open={!!selection} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full gap-0 sm:max-w-md">
        {m && (
          <>
            <SheetHeader className="border-b">
              <SheetTitle className="flex items-center gap-2 text-lg">
                <span aria-hidden>{m.icon}</span> {m.name}
              </SheetTitle>
              <SheetDescription>
                {m.title}
                {selection?.project ? ` · ${selection.project.name}` : " · the whole room"}
              </SheetDescription>
            </SheetHeader>
            <ScrollArea className="min-h-0 flex-1">
              <div className="space-y-5 p-4">
                <section className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={m.status} />
                    <span className="text-xs text-muted-foreground">{timeAgo(m.updated_at)}</span>
                  </div>
                  <p className="text-sm">{m.task ?? (m.status === "offline" ? "Hasn’t checked in yet." : "No current task.")}</p>
                  {m.source_url && (
                    <a className="inline-flex items-center gap-1 text-xs text-primary hover:underline" href={m.source_url} target="_blank" rel="noreferrer">
                      Open what they’re working on <ExternalLink className="size-3" />
                    </a>
                  )}
                </section>
                <section className="space-y-2">
                  <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">Waiting on you</h3>
                  {open.length ? (
                    open.map((i) => <ItemCard key={i.id} item={i} snapshot={snapshot} onResolve={onResolve} showProject={false} />)
                  ) : (
                    <p className="text-sm text-muted-foreground">Nothing. {m.name} isn’t waiting on you.</p>
                  )}
                </section>
                <Separator />
                <section className="space-y-2">
                  <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">Recent activity</h3>
                  <Timeline snapshot={snapshot} events={events} empty="No activity recorded yet." />
                </section>
              </div>
            </ScrollArea>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

export function ProjectSheet({
  snapshot,
  project,
  onClose,
  onResolve,
  onSelectMember,
}: {
  snapshot: RoomSnapshot;
  project: ProjectView | null;
  onClose: () => void;
  onResolve: Resolve;
  onSelectMember: (key: string) => void;
}) {
  const items = snapshot.items.filter((i) => project && i.project === project.id && i.status === "open");
  const events = snapshot.timeline.filter((e) => project && e.project === project.id);
  return (
    <Sheet open={!!project} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full gap-0 sm:max-w-md">
        {project && (
          <>
            <SheetHeader className="border-b">
              <SheetTitle className="flex items-center gap-2 text-lg">
                <span className={cn("size-2.5 rounded-full", HEALTH_DOT[project.health])} /> {project.name}
              </SheetTitle>
              <SheetDescription>
                {HEALTH_TEXT[project.health]} · {project.members.filter((m) => m.status !== "offline").length} of {project.members.length} in the pod
              </SheetDescription>
            </SheetHeader>
            <ScrollArea className="min-h-0 flex-1">
              <div className="space-y-5 p-4">
                {!!project.fires.length && (
                  <section className="space-y-2">
                    <h3 className="text-xs font-semibold tracking-wide text-red-500 uppercase">Fires</h3>
                    {project.fires.map((f) => (
                      <div key={f.key} className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm">
                        <p className="font-medium">🔥 {FIRE_LABEL[f.reason] ?? f.reason}</p>
                        {f.detail && <p className="mt-0.5">{f.detail}</p>}
                        <p className="mt-1 text-xs text-muted-foreground">
                          Since {timeAgo(f.since)}
                          {f.ref ? ` · ${f.ref}` : ""}
                          {f.alerted_at ? " · Maestro alerted you" : ""}
                        </p>
                      </div>
                    ))}
                  </section>
                )}
                <section className="space-y-2">
                  <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">Waiting on you</h3>
                  {items.length ? (
                    items.map((i) => <ItemCard key={i.id} item={i} snapshot={snapshot} onResolve={onResolve} showProject={false} />)
                  ) : (
                    <p className="text-sm text-muted-foreground">Nothing on this project needs you.</p>
                  )}
                </section>
                {!!project.risks.length && (
                  <section className="space-y-2">
                    <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">Open risks and blockers</h3>
                    {project.risks.map((r) => (
                      <div key={r.risk} className="rounded-lg border p-3 text-sm">
                        <p className="font-medium">{r.title ?? r.risk}</p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {r.kind === "blocker" ? "Blocker" : "Risk"}
                          {r.severity ? ` · ${r.severity}` : ""} · opened {timeAgo(r.opened_at)}
                          {r.ref ? ` · ${r.ref}` : ""}
                        </p>
                      </div>
                    ))}
                  </section>
                )}
                <section className="space-y-1">
                  <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">The squad</h3>
                  {project.members.map((m) => (
                    <button
                      key={m.id}
                      className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted"
                      onClick={() => onSelectMember(`${project.id}/${m.id}`)}
                    >
                      <span aria-hidden>{m.icon}</span>
                      <span className="w-16 shrink-0 font-medium">{m.name}</span>
                      <span className="min-w-0 flex-1 truncate text-muted-foreground">{m.task ?? STATUS_LABEL[m.status]}</span>
                      {m.asks + m.approvals > 0 && <Badge className="bg-amber-500 text-black">{m.asks + m.approvals}</Badge>}
                    </button>
                  ))}
                </section>
                <Separator />
                <section className="space-y-2">
                  <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">Timeline</h3>
                  <Timeline snapshot={snapshot} events={events} empty="No events on this project yet." />
                </section>
              </div>
            </ScrollArea>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

export function ApprovalsTray({ snapshot, open, onOpenChange, onResolve }: { snapshot: RoomSnapshot; open: boolean; onOpenChange: (o: boolean) => void; onResolve: Resolve }) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const approvals = useMemo(() => snapshot.items.filter((i) => i.kind === "approval" && i.status === "open"), [snapshot.items]);
  const asks = useMemo(() => snapshot.items.filter((i) => i.kind === "ask" && i.status === "open"), [snapshot.items]);
  const waiting = useMemo(() => snapshot.items.filter((i) => i.kind === "approval" && (i.status === "approved" || i.status === "edited")), [snapshot.items]);
  const live = [...selected].filter((id) => approvals.some((a) => a.id === id));

  const approve = async (ids: string[]) => {
    setBusy(true);
    const ok = await onResolve(ids.map((id) => ({ id, decision: "approved" as const })));
    setBusy(false);
    if (ok) setSelected(new Set());
  };

  const grouped = (list: typeof approvals) => {
    const by = new Map<string, typeof approvals>();
    for (const i of list) by.set(i.project, [...(by.get(i.project) ?? []), i]);
    return [...by.entries()];
  };
  const name = (id: string) => (id === ROOM_PROJECT ? "Room" : (snapshot.projects.find((p) => p.id === id)?.name ?? id));

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 sm:max-w-lg">
        <SheetHeader className="border-b">
          <SheetTitle className="text-lg">Waiting on you</SheetTitle>
          <SheetDescription>Nothing leaves the room until you approve it. Agents post what you approve on their next run.</SheetDescription>
        </SheetHeader>
        <Tabs defaultValue="approvals" className="min-h-0 flex-1 gap-0">
          <TabsList className="mx-4 mt-3">
            <TabsTrigger value="approvals">Approvals · {approvals.length}</TabsTrigger>
            <TabsTrigger value="asks">Questions · {asks.length}</TabsTrigger>
            <TabsTrigger value="waiting">Being posted · {waiting.length}</TabsTrigger>
          </TabsList>
          <TabsContent value="approvals" className="flex min-h-0 flex-1 flex-col">
            {snapshot.canAct && approvals.length > 0 && (
              <div className="flex items-center gap-2 border-b px-4 py-2.5">
                <Button size="sm" disabled={busy || !live.length} onClick={() => approve(live)}>
                  Approve selected ({live.length})
                </Button>
                <Button size="sm" variant="outline" disabled={busy} onClick={() => approve(approvals.map((a) => a.id))}>
                  Approve all {approvals.length}
                </Button>
              </div>
            )}
            <ScrollArea className="min-h-0 flex-1">
              <div className="space-y-4 p-4">
                {!approvals.length && <p className="text-sm text-muted-foreground">No hands raised. Every draft has been decided.</p>}
                {grouped(approvals).map(([pid, list]) => (
                  <section key={pid} className="space-y-2">
                    <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">{name(pid)}</h3>
                    {list.map((i) => (
                      <ItemCard
                        key={i.id}
                        item={i}
                        snapshot={snapshot}
                        onResolve={onResolve}
                        showProject={false}
                        selected={selected.has(i.id)}
                        onSelectedChange={(v) =>
                          setSelected((s) => {
                            const next = new Set(s);
                            if (v) next.add(i.id);
                            else next.delete(i.id);
                            return next;
                          })
                        }
                      />
                    ))}
                  </section>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>
          <TabsContent value="asks" className="min-h-0 flex-1">
            <ScrollArea className="h-full">
              <div className="space-y-2 p-4">
                {!asks.length && <p className="text-sm text-muted-foreground">No open questions.</p>}
                {asks.map((i) => (
                  <ItemCard key={i.id} item={i} snapshot={snapshot} onResolve={onResolve} />
                ))}
              </div>
            </ScrollArea>
          </TabsContent>
          <TabsContent value="waiting" className="min-h-0 flex-1">
            <ScrollArea className="h-full">
              <div className="space-y-2 p-4">
                {!waiting.length && <p className="text-sm text-muted-foreground">Nothing approved is waiting to be posted.</p>}
                {waiting.map((i) => (
                  <ItemCard key={i.id} item={i} snapshot={snapshot} onResolve={onResolve} />
                ))}
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
}

export function ListView({ snapshot, onSelectMember, onSelectProject }: { snapshot: RoomSnapshot; onSelectMember: (key: string) => void; onSelectProject: (id: string) => void }) {
  return (
    <div className="mx-auto grid max-w-6xl gap-3 p-3 sm:p-4 md:grid-cols-2 xl:grid-cols-3">
      {snapshot.projects.map((p) => (
        <section key={p.id} className={cn("rounded-xl border bg-card p-3", p.health === "red" && "border-red-500/60", p.health === "amber" && "border-amber-500/50")}>
          <button className="flex w-full items-center gap-2 text-left" onClick={() => onSelectProject(p.id)}>
            <span className={cn("size-2.5 rounded-full", HEALTH_DOT[p.health])} />
            <h2 className="flex-1 font-semibold">{p.name}</h2>
            {p.needs_you > 0 && <Badge variant="outline">? {p.needs_you}</Badge>}
            {p.approvals > 0 && <Badge variant="outline">✋ {p.approvals}</Badge>}
          </button>
          {p.fires.map((f) => (
            <p key={f.key} className="mt-2 rounded-md bg-red-500/10 px-2 py-1 text-sm text-red-600 dark:text-red-300">
              🔥 {FIRE_LABEL[f.reason] ?? f.reason}: {f.detail}
            </p>
          ))}
          <ul className="mt-2 divide-y">
            {p.members.map((m) => (
              <li key={m.id}>
                <button className="flex w-full items-center gap-2 py-1.5 text-left text-sm" onClick={() => onSelectMember(`${p.id}/${m.id}`)}>
                  <span aria-hidden>{m.icon}</span>
                  <span className="w-14 shrink-0 font-medium">{m.name}</span>
                  <span className={cn("min-w-0 flex-1 truncate", m.status === "offline" ? "text-muted-foreground/60" : "text-muted-foreground")}>
                    {m.status === "offline" ? "Away" : (m.task ?? STATUS_LABEL[m.status])}
                  </span>
                  {m.asks > 0 && <span title="Asked you a question">❓</span>}
                  {m.approvals > 0 && <span title="Raised a hand">✋</span>}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
