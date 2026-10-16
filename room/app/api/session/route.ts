import { cookies } from "next/headers";
import { checkPassword, newSession, SESSION_COOKIE } from "@/lib/aor/auth";

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as { password?: string } | null;
  if (!checkPassword(body?.password ?? "")) return Response.json({ error: "That password isn't right" }, { status: 401 });
  const s = newSession();
  (await cookies()).set(SESSION_COOKIE, s.value, { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", maxAge: s.maxAge, path: "/" });
  return Response.json({ ok: true });
}

export async function DELETE() {
  (await cookies()).delete(SESSION_COOKIE);
  return Response.json({ ok: true });
}
