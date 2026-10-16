import { cookies } from "next/headers";
import { Suspense } from "react";
import { RoomApp } from "@/components/room/room-app";
import { SignIn } from "@/components/room/sign-in";
import { passwordRequired, resolveAccess, SESSION_COOKIE } from "@/lib/aor/auth";

function Opening() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-3 bg-[#11131b] text-zinc-200">
      <div className="size-4 animate-bounce rounded-sm bg-amber-500" />
      <p className="text-sm text-zinc-400">Opening the room…</p>
    </main>
  );
}

async function Room({ searchParams }: { searchParams: PageProps<"/">["searchParams"] }) {
  const params = await searchParams;
  const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v);
  const token = one(params.token) ?? null;
  const access = resolveAccess((await cookies()).get(SESSION_COOKIE)?.value, token);
  if (access === "none") return <SignIn />;
  return <RoomApp kiosk={one(params.kiosk) === "1"} token={token} sound={one(params.sound) === "1"} passwordSet={passwordRequired()} />;
}

export default function Page({ searchParams }: PageProps<"/">) {
  return (
    <Suspense fallback={<Opening />}>
      <Room searchParams={searchParams} />
    </Suspense>
  );
}
