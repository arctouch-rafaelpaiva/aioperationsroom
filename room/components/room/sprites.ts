import type { RoleLook } from "@/lib/aor/roster";

export const TILE = 16;

export type Pose = "sit" | "type" | "read" | "raise" | "stretch" | "stand" | "walk";

type Ctx = CanvasRenderingContext2D;

const px = (ctx: Ctx, x: number, y: number, w: number, h: number, color: string) => {
  ctx.fillStyle = color;
  ctx.fillRect(Math.round(x), Math.round(y), w, h);
};

export function shade(hex: string, amount: number): string {
  const n = parseInt(hex.slice(1), 16);
  const f = (c: number) => Math.max(0, Math.min(255, Math.round(c + amount * 255)));
  return `#${[(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) => f(c).toString(16).padStart(2, "0")).join("")}`;
}

/** Cut-corner rectangle, the pixel-art rounded rect. */
export function block(ctx: Ctx, x: number, y: number, w: number, h: number, color: string) {
  px(ctx, x + 1, y, w - 2, h, color);
  px(ctx, x, y + 1, w, h - 2, color);
}

export const CHAR_W = 12;
export const CHAR_H = 18;

/**
 * Draws a front-facing character with its feet at (x, y) — x is the center.
 * `t` is time in seconds, used for blinking and limb cycles.
 */
export function drawCharacter(ctx: Ctx, cx: number, feetY: number, look: RoleLook, pose: Pose, t: number, opts: { maestro?: boolean; seed?: number } = {}) {
  const x = Math.round(cx - CHAR_W / 2);
  const step = pose === "walk" ? Math.floor(t * 8) % 2 : 0;
  const y = Math.round(feetY - CHAR_H) - step;
  const skin = look.skin;
  const shirt = look.shirt;
  const dark = shade(shirt, -0.18);
  const pants = opts.maestro ? "#111827" : "#334155";

  // Legs (hidden behind the desk when seated); walking lifts one foot per frame.
  if (pose === "walk" || pose === "stand") {
    const liftL = pose === "walk" && step === 1 ? 1 : 0;
    const liftR = pose === "walk" && step === 0 ? 1 : 0;
    px(ctx, x + 3, y + 14, 6, 2, pants);
    px(ctx, x + 3, y + 16, 2, 1, pants);
    px(ctx, x + 7, y + 16, 2, 1, pants);
    px(ctx, x + 2, y + 17 - liftL, 3, 1, "#1f2937");
    px(ctx, x + 7, y + 17 - liftR, 3, 1, "#1f2937");
  }

  // Body.
  px(ctx, x + 2, y + 8, 8, 6, shirt);
  px(ctx, x + 2, y + 13, 8, 1, dark);
  if (opts.maestro) {
    px(ctx, x + 5, y + 8, 2, 5, "#f9fafb");
    px(ctx, x + 4, y + 8, 4, 1, "#dc2626");
  } else {
    px(ctx, x + 5, y + 8, 2, 1, shade(shirt, 0.25));
  }
  px(ctx, x + 5, y + 7, 2, 1, skin);

  // Head.
  px(ctx, x + 3, y + 2, 6, 5, skin);
  px(ctx, x + 2, y + 0, 8, 3, look.hair);
  px(ctx, x + 2, y + 3, 1, 2, look.hair);
  px(ctx, x + 9, y + 3, 1, 2, look.hair);
  const blink = (t + (opts.seed ?? 0) * 1.7) % 4 < 0.12;
  const eyesY = pose === "read" ? y + 5 : y + 4;
  px(ctx, x + 4, eyesY, 1, blink ? 0 : 1, "#111827");
  px(ctx, x + 7, eyesY, 1, blink ? 0 : 1, "#111827");

  // Arms.
  const arm = (side: "l" | "r", mode: "down" | "desk" | "up" | "hold", phase = 0) => {
    const ax = side === "l" ? x + 1 : x + 10;
    if (mode === "down") {
      px(ctx, ax, y + 8, 1, 5, shirt);
      px(ctx, ax, y + 13, 1, 1, skin);
    } else if (mode === "desk") {
      px(ctx, ax, y + 8, 1, 4, shirt);
      px(ctx, side === "l" ? ax + 1 : ax - 1, y + 12 + phase, 2, 1, skin);
    } else if (mode === "up") {
      px(ctx, ax, y + 2, 1, 7, shirt);
      px(ctx, side === "l" ? ax - 1 : ax, y + 0, 2, 2, skin);
    } else {
      px(ctx, ax, y + 8, 1, 3, shirt);
    }
  };

  if (pose === "type") {
    const k = Math.floor(t * 10 + (opts.seed ?? 0)) % 2;
    arm("l", "desk", k);
    arm("r", "desk", 1 - k);
  } else if (pose === "read") {
    arm("l", "hold");
    arm("r", "hold");
    px(ctx, x + 2, y + 10, 8, 5, "#f8fafc");
    px(ctx, x + 6, y + 10, 1, 5, "#cbd5e1");
    px(ctx, x + 3, y + 11, 2, 1, "#94a3b8");
    px(ctx, x + 7, y + 11, 2, 1, "#94a3b8");
    px(ctx, x + 3, y + 13, 2, 1, "#94a3b8");
    px(ctx, x + 1, y + 11, 1, 1, skin);
    px(ctx, x + 10, y + 11, 1, 1, skin);
  } else if (pose === "raise") {
    arm("l", "down");
    arm("r", "up");
    // Wave the hand a little so a raised hand catches the eye.
    if (Math.floor(t * 3) % 2) px(ctx, x + 12, y + 0, 1, 2, skin);
  } else if (pose === "stretch") {
    arm("l", "up");
    arm("r", "up");
  } else {
    arm("l", "down");
    arm("r", "down");
  }
  if (opts.maestro && pose === "type") {
    px(ctx, x + 11, y + 6, 1, 6, "#f8fafc");
  }
}

export function drawChair(ctx: Ctx, cx: number, seatY: number, color = "#4c1d95") {
  const x = Math.round(cx - 5);
  block(ctx, x, seatY - 13, 10, 8, color);
  px(ctx, x + 2, seatY - 12, 6, 1, shade(color, 0.15));
  px(ctx, x + 4, seatY - 5, 2, 3, "#27272a");
}

export function drawDesk(ctx: Ctx, x: number, y: number, w: number, on: boolean, t: number, accent: string) {
  // Monitor (back), pushed to the left so the face stays visible.
  px(ctx, x, y - 10, 9, 8, "#1f2937");
  px(ctx, x + 1, y - 9, 7, 6, "#273244");
  px(ctx, x + 4, y - 2, 2, 2, "#111827");
  if (on) {
    const glow = 0.5 + 0.5 * Math.sin(t * 3);
    ctx.globalAlpha = 0.25 + glow * 0.2;
    px(ctx, x, y - 11, 9, 1, accent);
    ctx.globalAlpha = 1;
    px(ctx, x + 7, y - 4, 1, 1, "#22c55e");
  } else {
    px(ctx, x + 7, y - 4, 1, 1, "#52525b");
  }
  // Desk top and front.
  px(ctx, x, y, w, 4, "#a16207");
  px(ctx, x, y, w, 1, "#ca8a04");
  px(ctx, x, y + 4, w, 7, "#854d0e");
  px(ctx, x + 1, y + 11, 2, 2, "#713f12");
  px(ctx, x + w - 3, y + 11, 2, 2, "#713f12");
  // Mug and papers.
  px(ctx, x + w - 7, y - 3, 3, 3, "#e5e7eb");
  px(ctx, x + w - 4, y - 2, 1, 1, "#e5e7eb");
  px(ctx, x + w - 13, y + 1, 5, 2, "#f8fafc");
}

export function drawPlant(ctx: Ctx, x: number, y: number) {
  px(ctx, x + 3, y + 9, 6, 5, "#9a3412");
  px(ctx, x + 2, y + 9, 8, 1, "#c2410c");
  px(ctx, x + 4, y + 2, 4, 7, "#15803d");
  px(ctx, x + 1, y + 4, 4, 4, "#16a34a");
  px(ctx, x + 7, y + 3, 4, 5, "#16a34a");
  px(ctx, x + 5, y, 2, 3, "#22c55e");
}

export function drawTable(ctx: Ctx, x: number, y: number, w: number, h: number) {
  block(ctx, x, y + 2, w, h, "#3f2a1a");
  block(ctx, x, y, w, h, "#78350f");
  px(ctx, x + 2, y + 1, w - 4, 1, "#92400e");
  px(ctx, x + w / 2 - 6, y + 3, 5, 4, "#f8fafc");
  px(ctx, x + w / 2 + 2, y + 4, 4, 3, "#fde68a");
}

/** Speech bubble with a question mark, anchored above (cx, topY). */
export function drawAskBubble(ctx: Ctx, cx: number, topY: number, t: number) {
  const y = Math.round(topY - 13 - (Math.floor(t * 2) % 2));
  const x = Math.round(cx - 6);
  block(ctx, x - 1, y - 1, 14, 12, "#0f172a");
  block(ctx, x, y, 12, 10, "#ffffff");
  px(ctx, x + 4, y + 10, 3, 1, "#ffffff");
  px(ctx, x + 4, y + 11, 1, 1, "#0f172a");
  px(ctx, x + 5, y + 10, 2, 2, "#ffffff");
  // "?"
  px(ctx, x + 4, y + 2, 4, 1, "#2563eb");
  px(ctx, x + 7, y + 3, 1, 2, "#2563eb");
  px(ctx, x + 5, y + 5, 2, 1, "#2563eb");
  px(ctx, x + 5, y + 6, 1, 1, "#2563eb");
  px(ctx, x + 5, y + 8, 1, 1, "#2563eb");
}

/** Badge background; its number is drawn in the sharp text pass. */
export function drawBadge(ctx: Ctx, cx: number, cy: number, color: string) {
  block(ctx, cx - 4, cy - 4, 9, 9, "#0f172a");
  block(ctx, cx - 3, cy - 3, 7, 7, color);
}

/** Small state icon above the head: pencil (drafting), book (reading), moon (wrapping). */
export function drawStatusIcon(ctx: Ctx, cx: number, topY: number, kind: "drafting" | "reading" | "wrapping", t: number) {
  const y = Math.round(topY - 8 - (Math.floor(t * 1.5) % 2));
  const x = Math.round(cx - 3);
  if (kind === "drafting") {
    px(ctx, x, y + 4, 2, 2, "#fbbf24");
    px(ctx, x + 2, y + 2, 2, 2, "#fbbf24");
    px(ctx, x + 4, y, 2, 2, "#f87171");
    px(ctx, x - 1, y + 6, 1, 1, "#1f2937");
  } else if (kind === "reading") {
    px(ctx, x - 1, y, 4, 5, "#60a5fa");
    px(ctx, x + 3, y, 4, 5, "#3b82f6");
    px(ctx, x + 3, y, 1, 5, "#1e3a8a");
  } else {
    px(ctx, x, y, 4, 5, "#fde68a");
    px(ctx, x + 2, y, 3, 4, "#0f172a");
  }
}

export function drawFloor(ctx: Ctx, w: number, h: number) {
  for (let ty = 0; ty < h; ty += TILE) {
    for (let tx = 0; tx < w; tx += TILE) {
      px(ctx, tx, ty, TILE, TILE, ((tx + ty) / TILE) % 2 ? "#1c1f2a" : "#1f2330");
    }
  }
}

export function drawWall(ctx: Ctx, w: number, night: boolean) {
  px(ctx, 0, 0, w, TILE * 2, "#2a2f3f");
  px(ctx, 0, TILE * 2 - 2, w, 2, "#151824");
  for (let x = TILE; x + TILE * 3 < w; x += TILE * 6) {
    px(ctx, x, 6, TILE * 3, 16, "#0f172a");
    px(ctx, x + 1, 7, TILE * 3 - 2, 14, night ? "#1e1b4b" : "#7dd3fc");
    px(ctx, x + TILE * 1.5 - 1, 7, 1, 14, "#0f172a");
    if (night) {
      px(ctx, x + 8, 10, 1, 1, "#fef9c3");
      px(ctx, x + 30, 14, 1, 1, "#fef9c3");
    }
  }
}
