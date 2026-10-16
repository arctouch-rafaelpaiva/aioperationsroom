"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { RoomSnapshot } from "@/lib/aor/types";

const POLL_MS = 4000;
const MAX_BACKOFF_MS = 30000;

export type Connection = "connecting" | "live" | "retrying" | "signed-out";

export function useRoom(token: string | null) {
  const [snapshot, setSnapshot] = useState<RoomSnapshot | null>(null);
  const [connection, setConnection] = useState<Connection>("connecting");
  const [error, setError] = useState<string | null>(null);
  const failures = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const again = useRef<() => void>(() => {});

  const load = useCallback(async () => {
    if (timer.current) clearTimeout(timer.current);
    let delay = POLL_MS;
    try {
      const res = await fetch(`/api/state${token ? `?token=${encodeURIComponent(token)}` : ""}`, { cache: "no-store" });
      const body = await res.json().catch(() => ({ error: `The room answered ${res.status}` }));
      if (res.status === 401) {
        setConnection("signed-out");
        setError(body.error);
        return;
      }
      if (!res.ok) throw new Error(body.error ?? `The room answered ${res.status}`);
      setSnapshot(body);
      setConnection("live");
      setError(null);
      failures.current = 0;
    } catch (err) {
      failures.current += 1;
      delay = Math.min(MAX_BACKOFF_MS, POLL_MS * 2 ** failures.current);
      setConnection("retrying");
      setError((err as Error).message || "Can't reach the room");
    }
    timer.current = setTimeout(() => again.current(), delay);
  }, [token]);

  useEffect(() => {
    again.current = load;
    timer.current = setTimeout(load, 0);
    const onVisible = () => document.visibilityState === "visible" && load();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      if (timer.current) clearTimeout(timer.current);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [load]);

  return { snapshot, connection, error, refresh: load };
}
