import type { Member, ProjectView, RoomSnapshot } from "@/lib/aor/types";
import { TILE } from "./sprites";

export interface Seat {
  key: string;
  project: ProjectView | null;
  member: Member;
  x: number;
  feetY: number;
  deskX: number;
  deskY: number;
  deskW: number;
  meet: { x: number; y: number } | null;
}

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface PodLayout extends Rect {
  project: ProjectView;
  index: number;
  seats: Seat[];
  table: Rect;
  plate: Rect;
}

export interface WorldLayout {
  w: number;
  h: number;
  maestro: Seat;
  screen: Rect;
  pods: PodLayout[];
}

const SLOT = TILE * 3;
const DESK_W = TILE * 2;
const POD_H = TILE * 11;
const GAP = TILE;
const MAESTRO_H = TILE * 7;
const MIN_W = TILE * 22;

export const podWidth = (members: number) => Math.max(4, Math.ceil(members / 2)) * SLOT + TILE;

function chooseColumns(n: number, podW: number, aspect: number): number {
  let best = 1;
  let bestScale = 0;
  for (let c = 1; c <= Math.max(1, n); c++) {
    const rows = Math.ceil(n / c);
    const w = Math.max(MIN_W, c * (podW + GAP) + GAP);
    const h = MAESTRO_H + GAP + rows * (POD_H + GAP);
    const scale = Math.min(aspect / w, 1 / h);
    if (scale > bestScale + 1e-9) {
      best = c;
      bestScale = scale;
    }
  }
  return best;
}

export function computeLayout(snap: RoomSnapshot, aspect: number): WorldLayout {
  const n = snap.projects.length;
  const podW = Math.max(podWidth(7), ...snap.projects.map((p) => podWidth(p.members.length)));
  const cols = chooseColumns(n, podW, aspect);
  const rows = Math.ceil(n / cols);
  const w = Math.max(MIN_W, cols * (podW + GAP) + GAP);
  const h = MAESTRO_H + GAP + Math.max(rows, n ? 0 : 1) * (POD_H + GAP) + (n ? 0 : 0);

  const mDeskW = TILE * 4;
  const maestro: Seat = {
    key: `room/${snap.maestro.id}`,
    project: null,
    member: snap.maestro,
    x: w / 2,
    feetY: TILE * 5 + 2,
    deskX: w / 2 - mDeskW / 2,
    deskY: TILE * 5,
    deskW: mDeskW,
    meet: null,
  };
  const screen = { x: w / 2 - TILE * 4, y: 4, w: TILE * 8, h: 24 };

  const gridW = cols * (podW + GAP) + GAP;
  const offsetX = (w - gridW) / 2;

  const pods: PodLayout[] = snap.projects.map((project, index) => {
    const col = index % cols;
    const row = Math.floor(index / cols);
    const x = offsetX + GAP + col * (podW + GAP);
    const y = MAESTRO_H + GAP + row * (POD_H + GAP);
    const perRow = Math.max(4, Math.ceil(project.members.length / 2));
    const innerW = perRow * SLOT;
    const left = x + (podW - innerW) / 2;
    const tableW = Math.min(podW - TILE * 4, TILE * 7);
    const table = { x: x + (podW - tableW) / 2, y: y + 86, w: tableW, h: 18 };
    const topCount = Math.ceil(project.members.length / 2);
    const seats: Seat[] = project.members.map((member, i) => {
      const rowB = i >= topCount;
      const slot = rowB ? i - topCount : i;
      const rowCount = rowB ? project.members.length - topCount : topCount;
      const rowLeft = left + ((perRow - rowCount) * SLOT) / 2;
      const deskY = y + (rowB ? 140 : 52);
      const cx = rowLeft + slot * SLOT + SLOT / 2;
      const spread = table.w / Math.max(1, rowCount);
      return {
        key: `${project.id}/${member.id}`,
        project,
        member,
        x: cx,
        feetY: deskY + 2,
        deskX: cx - DESK_W / 2,
        deskY,
        deskW: DESK_W,
        meet: { x: table.x + spread * slot + spread / 2, y: rowB ? table.y + table.h + 22 : table.y + 2 },
      };
    });
    return { project, index, x, y, w: podW, h: POD_H, seats, table, plate: { x: x + 6, y: y + 5, w: podW - 12, h: 14 } };
  });

  return { w, h: Math.max(h, MAESTRO_H + GAP + POD_H + GAP), maestro, screen, pods };
}
