"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function SignIn({ message }: { message?: string }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  return (
    <main className="flex min-h-dvh items-center justify-center bg-[#11131b] p-4 text-zinc-100">
      <form
        className="w-full max-w-sm space-y-4 rounded-xl border border-white/10 bg-zinc-950 p-6 shadow-2xl"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          const res = await fetch("/api/session", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) });
          if (res.ok) window.location.reload();
          else {
            setError((await res.json().catch(() => ({}))).error ?? "Couldn't sign in");
            setBusy(false);
          }
        }}
      >
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-lg font-semibold">
            <span className="grid size-6 place-items-center rounded bg-amber-500 text-sm text-black" aria-hidden>
              ◆
            </span>
            AI Operations Room
          </div>
          <p className="text-sm text-zinc-400">{message ?? "Sign in as the operator to see the room and decide what gets posted."}</p>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Operator password</Label>
          <Input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} autoFocus />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <Button className="w-full" type="submit" disabled={busy || !password}>
          {busy ? "Signing in…" : "Enter the room"}
        </Button>
        <p className="text-xs text-zinc-500">Wall screens can open the room view-only with the kiosk link instead.</p>
      </form>
    </main>
  );
}
