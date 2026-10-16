"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { lookFor } from "@/lib/aor/roster";
import type { Health, RoomSnapshot } from "@/lib/aor/types";
import { computeLayout, type PodLayout, type Seat, type WorldLayout } from "./layout";
import {
  block,
  CHAR_H,
  drawAskBubble,
  drawBadge,
  drawChair,
  drawCharacter,
  drawDesk,
  drawFloor,
  drawPlant,
  drawStatusIcon,
  drawTable,
  drawWall,
  shade,
  type Pose,
} from "./sprites";

const CARPETS = ["#27324a", "#33294a", "#22403b", "#43322a", "#2d3b29", "#3d2838"];
const HEALTH: Record<Health, string> = { green: "#22c55e", amber: "#f59e0b", red: "#ef4444" };
const WALK_SPEED = 40; // world px per second

interface Walker {
  x: number;
  y: number;
}

export interface Hover {
  kind: "member" | "project";
  key: string;
  label: string;
  sub: string;
  detail?: string;
  left: number;
  top: number;
}

interface Props {
  snapshot: RoomSnapshot;
  night: boolean;
  selectedKey: string | null;
  onSelectMember: (key: string) => void;
  onSelectProject: (id: string) => void;
}

function poseFor(seat: Seat, atHome: boolean, moving: boolean, t: number): Pose {
  if (moving) return "walk";
  if (!atHome) return "stand";
  const m = seat.member;
  if (m.approvals > 0) return "raise";
  switch (m.status) {
    case "working":
    case "drafting":
      return "type";
    case "reading":
      return "read";
    case "wrapping":
      return t % 6 < 1.4 ? "stretch" : "sit";
    default:
      return "sit";
  }
}

export function RoomCanvas({ snapshot, night, selectedKey, onSelectMember, onSelectProject }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [size, setSize] = useState({ w: 800, h: 600 });
  const [hover, setHover] = useState<Hover | null>(null);
  const walkers = useRef(new Map<string, Walker>());
  const view = useRef({ scale: 1, ox: 0, oy: 0 });
  const live = useRef({ snapshot, night, selectedKey, hoverKey: null as string | null });
  const layout = useMemo(() => computeLayout(snapshot, size.w / Math.max(1, size.h)), [snapshot, size]);
  const layoutRef = useRef<WorldLayout>(layout);

  useEffect(() => {
    live.current = { snapshot, night, selectedKey, hoverKey: hover?.key ?? null };
    layoutRef.current = layout;
  });

  useEffect(() => {
    walkers.current.clear();
  }, [layout.w, layout.h]);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setSize({ w: entry.contentRect.width, h: entry.contentRect.height }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    const off = document.createElement("canvas");
    const octx = off.getContext("2d")!;
    let raf = 0;
    let last = performance.now();
    const start = last;

    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      const t = (now - start) / 1000;
      const L = layoutRef.current;
      const { snapshot: snap, night: dim, selectedKey: sel, hoverKey } = live.current;
      const dpr = window.devicePixelRatio || 1;
      const cw = canvas.clientWidth;
      const ch = canvas.clientHeight;
      if (canvas.width !== Math.round(cw * dpr) || canvas.height !== Math.round(ch * dpr)) {
        canvas.width = Math.round(cw * dpr);
        canvas.height = Math.round(ch * dpr);
      }
      if (off.width !== L.w || off.height !== L.h) {
        off.width = L.w;
        off.height = L.h;
      }
      const fit = Math.min(cw / L.w, ch / L.h);
      const scale = fit >= 1 ? Math.floor(fit * 4) / 4 : fit;
      const ox = (cw - L.w * scale) / 2;
      const oy = (ch - L.h * scale) / 2;
      view.current = { scale, ox, oy };

      drawWorld(octx, L, snap, t, dt, walkers.current, sel, hoverKey);

      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = "#11131b";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(off, ox * dpr, oy * dpr, L.w * scale * dpr, L.h * scale * dpr);
      ctx.setTransform(dpr * scale, 0, 0, dpr * scale, ox * dpr, oy * dpr);
      drawText(ctx, L, snap, walkers.current, t);
      if (dim) {
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.fillStyle = "rgba(8, 10, 30, 0.38)";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, []);

  const toWorld = (clientX: number, clientY: number) => {
    const r = canvasRef.current!.getBoundingClientRect();
    const { scale, ox, oy } = view.current;
    return { x: (clientX - r.left - ox) / scale, y: (clientY - r.top - oy) / scale, sx: clientX - r.left, sy: clientY - r.top };
  };

  const hit = (clientX: number, clientY: number): Hover | null => {
    const { x, y, sx, sy } = toWorld(clientX, clientY);
    const L = layoutRef.current;
    for (const seat of [L.maestro, ...L.pods.flatMap((p) => p.seats)]) {
      if (seat.member.status === "offline") continue;
      const w = walkers.current.get(seat.key) ?? { x: seat.x, y: seat.feetY };
      if (x >= w.x - 8 && x <= w.x + 8 && y >= w.y - CHAR_H - 2 && y <= w.y + 6) {
        const m = seat.member;
        return {
          kind: "member",
          key: seat.key,
          label: `${m.icon} ${m.name}`,
          sub: seat.project ? `${m.title} · ${seat.project.name}` : m.title,
          detail: m.task ? `${m.status}: ${m.task}` : m.status,
          left: sx,
          top: sy,
        };
      }
    }
    for (const pod of L.pods) {
      if (x >= pod.x && x <= pod.x + pod.w && y >= pod.y && y <= pod.y + 22) {
        const p = pod.project;
        const bits = [p.fires.length ? `${p.fires.length} fire${p.fires.length > 1 ? "s" : ""}` : "", p.needs_you ? `${p.needs_you} need you` : "", p.approvals ? `${p.approvals} to approve` : ""].filter(Boolean);
        return { kind: "project", key: p.id, label: p.name, sub: bits.join(" · ") || "All calm", left: sx, top: sy };
      }
    }
    return null;
  };

  return (
    <div ref={wrapRef} className="relative h-full w-full overflow-hidden">
      <canvas
        ref={canvasRef}
        className="h-full w-full"
        style={{ cursor: hover ? "pointer" : "default", imageRendering: "pixelated" }}
        role="img"
        aria-label={`Operations room with ${snapshot.projects.length} project pods`}
        onMouseMove={(e) => setHover(hit(e.clientX, e.clientY))}
        onMouseLeave={() => setHover(null)}
        onClick={(e) => {
          const h = hit(e.clientX, e.clientY);
          if (h?.kind === "member") onSelectMember(h.key);
          if (h?.kind === "project") onSelectProject(h.key);
        }}
      />
      {hover && (
        <div
          className="pointer-events-none absolute z-10 max-w-72 rounded-md border border-white/10 bg-zinc-950/95 px-3 py-2 text-xs text-zinc-100 shadow-xl"
          style={{ left: Math.min(hover.left + 14, size.w - 290), top: Math.max(8, hover.top - 64) }}
        >
          <div className="font-semibold">{hover.label}</div>
          <div className="text-zinc-400">{hover.sub}</div>
          {hover.detail && <div className="mt-1 text-zinc-200">{hover.detail}</div>}
        </div>
      )}
    </div>
  );
}

function stepWalker(seat: Seat, walkers: Map<string, Walker>, dt: number) {
  const home = { x: seat.x, y: seat.feetY };
  const target = seat.member.status === "meeting" && seat.meet ? seat.meet : home;
  let w = walkers.get(seat.key);
  if (!w) {
    w = { ...target };
    walkers.set(seat.key, w);
  }
  const step = WALK_SPEED * dt;
  const dx = target.x - w.x;
  const dy = target.y - w.y;
  // L-shaped path: leave the desk row vertically, then cross; on the way back, cross first, then sit.
  const moveX = target === home ? Math.abs(dx) > 0.5 : Math.abs(dy) <= 0.5;
  if (moveX && Math.abs(dx) > 0.5) w.x += Math.sign(dx) * Math.min(step, Math.abs(dx));
  else if (Math.abs(dy) > 0.5) w.y += Math.sign(dy) * Math.min(step, Math.abs(dy));
  else if (Math.abs(dx) > 0.5) w.x += Math.sign(dx) * Math.min(step, Math.abs(dx));
  const atHome = Math.abs(w.x - home.x) < 0.5 && Math.abs(w.y - home.y) < 0.5;
  const moving = Math.abs(w.x - target.x) > 0.5 || Math.abs(w.y - target.y) > 0.5;
  return { w, atHome, moving };
}

function drawPod(ctx: CanvasRenderingContext2D, pod: PodLayout, t: number) {
  const p = pod.project;
  const carpet = CARPETS[pod.index % CARPETS.length];
  const ring = HEALTH[p.health];
  const flash = p.health === "red" && Math.floor(t * 2.5) % 2 === 0;
  block(ctx, pod.x - 2, pod.y - 2, pod.w + 4, pod.h + 4, flash ? "#ef4444" : shade(ring, -0.35));
  block(ctx, pod.x, pod.y, pod.w, pod.h, carpet);
  for (let yy = pod.y + 26; yy < pod.y + pod.h - 4; yy += 8) {
    ctx.fillStyle = shade(carpet, 0.03);
    ctx.fillRect(pod.x + 4, yy, pod.w - 8, 1);
  }
  block(ctx, pod.plate.x, pod.plate.y, pod.plate.w, pod.plate.h, "#0b0d14");
  // Health light, with a rotating siren beam when the pod is on fire.
  const lx = pod.plate.x + 8;
  const ly = pod.plate.y + 7;
  ctx.fillStyle = ring;
  ctx.globalAlpha = p.health === "red" ? 0.6 + 0.4 * Math.sin(t * 10) : 1;
  ctx.fillRect(lx - 2, ly - 2, 5, 5);
  ctx.globalAlpha = 0.25;
  ctx.fillRect(lx - 4, ly - 4, 9, 9);
  ctx.globalAlpha = 1;
  if (p.health === "red") {
    ctx.globalAlpha = 0.12 + 0.1 * Math.sin(t * 5);
    ctx.fillStyle = "#ef4444";
    ctx.fillRect(pod.x, pod.y, pod.w, pod.h);
    ctx.globalAlpha = 1;
  }
  drawTable(ctx, pod.table.x, pod.table.y, pod.table.w, pod.table.h);
  drawPlant(ctx, pod.x + 2, pod.y + pod.h - 18);
  drawPlant(ctx, pod.x + pod.w - 14, pod.y + pod.h - 18);
}

function drawWorld(
  ctx: CanvasRenderingContext2D,
  L: WorldLayout,
  snap: RoomSnapshot,
  t: number,
  dt: number,
  walkers: Map<string, Walker>,
  selectedKey: string | null,
  hoverKey: string | null,
) {
  ctx.imageSmoothingEnabled = false;
  drawFloor(ctx, L.w, L.h);
  drawWall(ctx, L.w, false);

  // Maestro's wall screen and command desk.
  const s = L.screen;
  const anyFire = snap.projects.some((p) => p.health === "red");
  const anyAmber = snap.projects.some((p) => p.health === "amber") || snap.items.some((i) => i.status === "open");
  block(ctx, s.x - 2, s.y - 2, s.w + 4, s.h + 4, "#0b0d14");
  block(ctx, s.x, s.y, s.w, s.h, anyFire && Math.floor(t * 2.5) % 2 === 0 ? "#450a0a" : "#0f1a2e");
  const lamp = anyFire ? HEALTH.red : anyAmber ? HEALTH.amber : HEALTH.green;
  ctx.fillStyle = lamp;
  ctx.fillRect(s.x + 4, s.y + 4, 4, 4);
  drawPlant(ctx, 8, 40);
  drawPlant(ctx, L.w - 20, 40);
  block(ctx, L.maestro.deskX - 10, L.maestro.deskY - 22, L.maestro.deskW + 20, 40, "#1a1d29");

  type Drawable = { y: number; draw: () => void };
  const drawables: Drawable[] = [];
  const overlays: (() => void)[] = [];

  for (const pod of L.pods) drawPod(ctx, pod, t);

  const seats = [L.maestro, ...L.pods.flatMap((p) => p.seats)];
  for (const seat of seats) {
    const m = seat.member;
    const look = lookFor(m.role);
    const isMaestro = seat.project === null;
    const accent = look.shirt;
    const offline = m.status === "offline";
    const { w, atHome, moving } = stepWalker(seat, walkers, dt);
    const seated = atHome && !offline;
    const deskOn = seated && ["working", "drafting", "reading"].includes(m.status);
    drawChair(ctx, seat.x, seat.feetY, isMaestro ? "#7f1d1d" : shade(accent, -0.3));
    if (!offline) {
      const pose = poseFor(seat, atHome, moving, t);
      const seed = seat.key.length;
      drawables.push({
        y: seated ? seat.deskY + 11 : w.y,
        draw: () => {
          if (selectedKey === seat.key || hoverKey === seat.key) {
            ctx.fillStyle = selectedKey === seat.key ? "#fde047" : "#ffffff";
            ctx.globalAlpha = 0.35;
            ctx.fillRect(Math.round(w.x - 8), Math.round(w.y - CHAR_H - 2), 16, CHAR_H + 2);
            ctx.globalAlpha = 1;
          }
          drawCharacter(ctx, w.x, w.y, look, pose, t, { maestro: isMaestro, seed });
          if (seated) drawDesk(ctx, seat.deskX, seat.deskY, seat.deskW, deskOn, t, accent);
        },
      });
      if (!seated) drawables.push({ y: seat.deskY + 11, draw: () => drawDesk(ctx, seat.deskX, seat.deskY, seat.deskW, false, t, accent) });
      overlays.push(() => {
        const top = w.y - CHAR_H;
        if (m.asks > 0) drawAskBubble(ctx, w.x, top, t);
        else if (m.approvals > 0) drawBadge(ctx, w.x + 9, top - 4, "#f59e0b");
        else if (atHome && (m.status === "drafting" || m.status === "reading" || m.status === "wrapping")) drawStatusIcon(ctx, w.x, top, m.status, t);
      });
    } else {
      drawables.push({ y: seat.deskY + 11, draw: () => drawDesk(ctx, seat.deskX, seat.deskY, seat.deskW, false, t, accent) });
    }
  }

  drawables.sort((a, b) => a.y - b.y).forEach((d) => d.draw());
  overlays.forEach((o) => o());
}

function drawText(ctx: CanvasRenderingContext2D, L: WorldLayout, snap: RoomSnapshot, walkers: Map<string, Walker>, t: number) {
  ctx.textBaseline = "middle";
  const s = L.screen;
  const open = snap.items.filter((i) => i.status === "open");
  const fires = snap.projects.reduce((n, p) => n + p.fires.length, 0);
  const asks = open.filter((i) => i.kind === "ask").length;
  const approvals = open.length - asks;
  ctx.textAlign = "center";
  ctx.font = "bold 6px ui-monospace, SFMono-Regular, Menlo, monospace";
  ctx.fillStyle = "#e2e8f0";
  ctx.fillText("AI OPERATIONS ROOM", s.x + s.w / 2, s.y + 7);
  ctx.font = "5px ui-monospace, SFMono-Regular, Menlo, monospace";
  ctx.fillStyle = fires ? "#fca5a5" : asks || approvals ? "#fcd34d" : "#86efac";
  const summary = fires ? `${fires} FIRE${fires > 1 ? "S" : ""} · ${asks} NEED YOU · ${approvals} TO APPROVE` : asks || approvals ? `${asks} NEED YOU · ${approvals} TO APPROVE` : "ALL CALM";
  ctx.fillText(summary, s.x + s.w / 2, s.y + 17);

  for (const pod of L.pods) {
    const p = pod.project;
    ctx.textAlign = "left";
    ctx.font = "bold 7px ui-sans-serif, system-ui, sans-serif";
    ctx.fillStyle = "#f8fafc";
    const counts = [p.needs_you ? `? ${p.needs_you}` : "", p.approvals ? `✋ ${p.approvals}` : ""].filter(Boolean).join("  ");
    const maxName = pod.plate.w - 24 - counts.length * 4.5;
    let name = p.name;
    while (ctx.measureText(name).width > maxName && name.length > 3) name = name.slice(0, -2) + "…";
    ctx.fillText(name, pod.plate.x + 15, pod.plate.y + 7.5);
    if (counts) {
      ctx.textAlign = "right";
      ctx.font = "bold 6px ui-sans-serif, system-ui, sans-serif";
      ctx.fillStyle = "#fcd34d";
      ctx.fillText(counts, pod.plate.x + pod.plate.w - 5, pod.plate.y + 7.5);
    }
    if (p.health === "red" && p.fires[0]) {
      ctx.textAlign = "center";
      ctx.font = "bold 5.5px ui-sans-serif, system-ui, sans-serif";
      ctx.fillStyle = Math.floor(t * 2.5) % 2 ? "#fecaca" : "#ffffff";
      const label = `🔥 ${p.fires[0].reason.replace(/_/g, " ")}`;
      ctx.fillText(label, pod.table.x + pod.table.w / 2, pod.table.y - 7);
    }
  }

  ctx.textAlign = "center";
  ctx.font = "4.5px ui-sans-serif, system-ui, sans-serif";
  for (const seat of [L.maestro, ...L.pods.flatMap((p) => p.seats)]) {
    const m = seat.member;
    ctx.fillStyle = m.status === "offline" ? "#52525b" : "#cbd5e1";
    ctx.fillText(m.status === "offline" ? `${m.name} · away` : m.name, seat.x, seat.deskY + 16.5);
    const w = walkers.get(seat.key);
    if (m.approvals > 0 && m.asks === 0 && w && m.status !== "offline") {
      ctx.font = "bold 5px ui-sans-serif, system-ui, sans-serif";
      ctx.fillStyle = "#0f172a";
      ctx.fillText(m.approvals > 9 ? "+" : String(m.approvals), w.x + 9.5, w.y - CHAR_H - 3.5);
      ctx.font = "4.5px ui-sans-serif, system-ui, sans-serif";
    }
  }
}
