import { cookies } from "next/headers";
import { resolveAccess, SESSION_COOKIE } from "@/lib/aor/auth";
import { getSnapshot } from "@/lib/aor/room";

export async function GET(request: Request) {
  const token = new URL(request.url).searchParams.get("token");
  const access = resolveAccess((await cookies()).get(SESSION_COOKIE)?.value, token);
  if (access === "none") return Response.json({ error: "Sign in to see the room" }, { status: 401 });
  try {
    return Response.json(await getSnapshot(access === "operator"), { headers: { "Cache-Control": "no-store" } });
  } catch (err) {
    return Response.json({ error: `Couldn't read the ops repo: ${(err as Error).message}` }, { status: 502 });
  }
}
