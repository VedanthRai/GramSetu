import { useEffect, useState } from "react";
import { Gauge } from "lucide-react";
import { api, type ProvidersStatus, type Usage } from "../lib/api";
import { Badge } from "./Layout";
import type { TurnLatency } from "./VoicePanel";

export function useProviders(intervalMs = 15000) {
  const [p, setP] = useState<ProvidersStatus | null>(null);
  const [u, setU] = useState<Usage | null>(null);
  useEffect(() => {
    let alive = true;
    const load = () => {
      api.providers().then((x) => alive && setP(x)).catch(() => undefined);
      api.usage().then((x) => alive && setU(x)).catch(() => undefined);
    };
    load();
    const t = window.setInterval(load, intervalMs);
    return () => { alive = false; window.clearInterval(t); };
  }, [intervalMs]);
  return { providers: p, usage: u };
}

function dot(ok: boolean | null, configured: boolean) {
  if (!configured) return "bg-danger";
  if (ok === null) return "bg-ink-faint";
  return ok ? "bg-verified" : "bg-danger";
}

export function ProviderStrip({ providers, usage }: { providers: ProvidersStatus | null; usage: Usage | null }) {
  if (!providers) return null;
  const items = [
    { k: "STT", h: providers.stt, label: `${providers.stt.name} · ${providers.stt.model ?? ""}` },
    { k: "TTS", h: providers.tts, label: `${providers.tts.name} · ${providers.tts.model ?? ""}` },
    { k: "Reasoning", h: providers.reasoning, label: providers.reasoning.is_ai ? `${providers.reasoning.label} · ${providers.reasoning.model}` : String(providers.reasoning.label) },
  ];
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs" aria-label="Provider status">
      {items.map(({ k, h, label }) => (
        <span key={k} className="inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-2.5 py-1"
          title={h.last_error ? `Last error: ${h.last_error}` : h.last_latency_ms != null ? `Last call ${h.last_latency_ms} ms` : "Not called yet"}>
          <span className={`h-2 w-2 rounded-full ${dot(h.reachable, h.configured)}`} aria-hidden />
          <span className="font-semibold">{k}:</span> {label}
          {h.reachable === false && <span className="text-danger">(error)</span>}
        </span>
      ))}
      {usage?.fixture_mode && <Badge tone="danger">Fixture mode — recorded Gnani responses</Badge>}
      {usage && (
        <span className="rounded-full border border-line bg-white px-2.5 py-1" title={usage.label}>
          Gnani requests today: <b>{usage.today_calls}</b>/{usage.daily_limit} <span className="text-ink-faint">(local count, not official credits)</span>
        </span>
      )}
    </div>
  );
}

export function LatencyHud({ l }: { l: TurnLatency }) {
  const [open, setOpen] = useState(true);
  const rows: [string, string][] = [
    ["Recording length", l.recordingS != null ? `${l.recordingS} s` : "—"],
    ["Prisma transcription", l.prismaMs != null ? `${l.prismaMs} ms` : "—"],
    ["Reasoning", l.reasoningMs != null ? `${l.reasoningMs} ms` : "—"],
    ["Timbre time-to-first-audio", l.ttfaMs != null ? `${l.ttfaMs} ms${l.ttsCache === "hit" ? " (cached phrase)" : l.ttsServerMs ? ` (API ${l.ttsServerMs} ms)` : ""}` : "—"],
    ["Total machine time (Prisma + send → first reply audio)", l.sendToAudioMs != null ? `${(((l.prismaMs ?? 0) + l.sendToAudioMs) / 1000).toFixed(2)} s` : "—"],
  ];
  return (
    <div className="rounded-xl border border-line bg-card" data-testid="latency-hud">
      <button className="flex w-full items-center justify-between px-4 py-3 text-sm font-semibold uppercase tracking-wide text-ink-soft" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <span className="inline-flex items-center gap-2"><Gauge className="h-4 w-4" aria-hidden />Latency HUD — this turn, measured</span>
        <span aria-hidden>{open ? "–" : "+"}</span>
      </button>
      {open && (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 px-4 pb-4 text-sm sm:grid-cols-5">
          {rows.map(([k, v]) => (
            <div key={k}>
              <dt className="text-xs text-ink-faint">{k}</dt>
              <dd className="font-mono font-semibold">{v}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
