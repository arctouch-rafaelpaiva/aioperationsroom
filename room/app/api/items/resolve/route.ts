import { cookies } from "next/headers";
import { resolveAccess, SESSION_COOKIE } from "@/lib/aor/auth";
import { resolveItems, type ResolveRequest } from "@/lib/aor/room";

export async function POST(request: Request) {
  if (resolveAccess((await cookies()).get(SESSION_COOKIE)?.value, null) !== "operator") {
    return Response.json({ error: "Only the signed-in operator can decide" }, { status: 403 });
  }
  const body = (await request.json().catch(() => null)) as { items?: ResolveRequest[] } | null;
  if (!Array.isArray(body?.items) || !body.items.length) return Response.json({ error: "items must be a non-empty list" }, { status: 400 });
  try {
    const results = await resolveItems(body.items, "operator");
    return Response.json({ results }, { status: results.some((r) => r.ok) ? 200 : 409 });
  } catch (err) {
    return Response.json({ error: `Couldn't record the decision: ${(err as Error).message}` }, { status: 502 });
  }
}
