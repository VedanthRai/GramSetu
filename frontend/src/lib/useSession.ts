import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type LangCode, type SessionSnapshot, type TimelineEvent } from "./api";

export type WsStatus = "connecting" | "open" | "closed";

export function useSession() {
  const [session, setSession] = useState<SessionSnapshot | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [ws, setWs] = useState<WsStatus>("closed");
  const [error, setError] = useState<string | null>(null);
  const sidRef = useRef<string | null>(null);
  const refetchTimer = useRef<number | null>(null);

  const refetch = useCallback(() => {
    if (refetchTimer.current) window.clearTimeout(refetchTimer.current);
    refetchTimer.current = window.setTimeout(async () => {
      const sid = sidRef.current;
      if (!sid) return;
      try {
        const r = await api.getSession(sid);
        if (sidRef.current === sid) setSession(r.session);
      } catch {
        /* transient: next event refetches */
      }
    }, 120);
  }, []);

  // WebSocket with automatic reconnect; on reconnect we refetch full state so nothing is missed.
  useEffect(() => {
    const sid = session?.id;
    if (!sid) return;
    let socket: WebSocket | null = null;
    let stopped = false;
    let retry = 0;
    let ping: number | undefined;
    const connect = () => {
      setWs("connecting");
      const proto = location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${proto}://${location.host}/api/ws/sessions/${sid}`);
      socket.onopen = () => {
        retry = 0;
        setWs("open");
        refetch();
        api.events(sid).then((r) => setEvents(r.events)).catch(() => undefined);
        ping = window.setInterval(() => socket?.readyState === 1 && socket.send("ping"), 20000);
      };
      socket.onmessage = (m) => {
        const payload = JSON.parse(m.data as string) as { type: string } & Partial<TimelineEvent>;
        if (payload.type === "event" && payload.kind !== "message") {
          setEvents((prev) => (prev.some((e) => e.id === payload.id) ? prev : [...prev, payload as TimelineEvent]));
        }
        refetch();
      };
      socket.onclose = () => {
        window.clearInterval(ping);
        setWs("closed");
        if (!stopped) window.setTimeout(connect, Math.min(8000, 500 * 2 ** retry++));
      };
    };
    connect();
    return () => {
      stopped = true;
      window.clearInterval(ping);
      socket?.close();
    };
  }, [session?.id, refetch]);

  const run = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | null> => {
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Network problem. Check your connection and try again.");
      return null;
    }
  }, []);

  const start = useCallback(async (language: LangCode, retain: boolean) => {
    const r = await run(() => api.createSession(language, retain));
    if (r) {
      sidRef.current = r.session.id;
      setEvents([]);
      setSession(r.session);
    }
    return r?.session ?? null;
  }, [run]);

  const apply = useCallback((r: { session: SessionSnapshot } | null) => {
    if (r) setSession(r.session);
    return r;
  }, []);

  return {
    session, events, ws, error, setError, start, refetch,
    turn: (text: string, raw?: string, choice?: { field: string; value: string }) =>
      run(() => api.turn(sidRef.current!, text, raw, choice)).then(apply),
    review: () => run(() => api.review(sidRef.current!)).then(apply),
    approve: (kind: "start" | "final") => run(() => api.approve(sidRef.current!, kind)).then(apply),
    cancel: () => run(() => api.cancel(sidRef.current!)).then(apply),
    secureInput: (v: string) => run(() => api.userInput(sidRef.current!, v)).then(apply),
    resume: () => run(() => api.resume(sidRef.current!)).then(apply),
    remove: async () => {
      const sid = sidRef.current;
      if (!sid) return;
      await run(() => api.deleteSession(sid));
      sidRef.current = null;
      setSession(null);
      setEvents([]);
    },
  };
}

export type SessionApi = ReturnType<typeof useSession>;
