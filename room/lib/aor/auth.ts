import { createHmac, timingSafeEqual } from "node:crypto";

export type Access = "operator" | "viewer" | "none";

export const SESSION_COOKIE = "aor_session";
const SESSION_DAYS = 14;

function secret(): string {
  return process.env.AOR_SESSION_SECRET || process.env.AOR_ROOM_TOKEN || process.env.AOR_OPERATOR_PASSWORD || "";
}

function sign(value: string) {
  return createHmac("sha256", secret()).update(value).digest("hex");
}

export function safeEqual(a: string, b: string) {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
}

export function passwordRequired(): boolean {
  return !!process.env.AOR_OPERATOR_PASSWORD;
}

/** Shared deployments (GitHub-backed) must set a password before anyone can act. */
export function actionsLocked(): boolean {
  return !passwordRequired() && !!process.env.AOR_GITHUB_REPO && !process.env.AOR_OPS_DIR;
}

export function checkPassword(candidate: string): boolean {
  const pw = process.env.AOR_OPERATOR_PASSWORD;
  return !!pw && safeEqual(candidate, pw);
}

export function newSession(now = Date.now()): { value: string; maxAge: number } {
  const expires = now + SESSION_DAYS * 86_400_000;
  return { value: `${expires}.${sign(`operator.${expires}`)}`, maxAge: SESSION_DAYS * 86_400 };
}

function validSession(value: string | undefined, now = Date.now()): boolean {
  if (!value) return false;
  const [expires, mac] = value.split(".");
  return Number(expires) > now && !!mac && safeEqual(mac, sign(`operator.${expires}`));
}

/**
 * Operator: logged in, or no password configured on a local or demo room.
 * Viewer: the kiosk token (view-only), or any visitor when no password is set.
 */
export function resolveAccess(session: string | undefined, kioskToken: string | null | undefined): Access {
  if (!passwordRequired()) return actionsLocked() ? "viewer" : "operator";
  if (validSession(session)) return "operator";
  const kiosk = process.env.AOR_KIOSK_TOKEN;
  if (kiosk && kioskToken && safeEqual(kioskToken, kiosk)) return "viewer";
  return "none";
}

export function bearerOk(header: string | null): boolean {
  const token = process.env.AOR_ROOM_TOKEN;
  if (!token || !header?.startsWith("Bearer ")) return false;
  return safeEqual(header.slice(7), token);
}
