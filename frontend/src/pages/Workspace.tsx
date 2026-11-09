import { useCallback, useEffect, useRef, useState } from "react";
import { Plus, RotateCcw, Trash2 } from "lucide-react";
import { api, type Language, type LangCode } from "../lib/api";
import { speaker } from "../audio/player";
import { useSettings } from "../lib/settings";
import { useSession } from "../lib/useSession";
import { ui } from "../lib/ui";
import { VoicePanel, type TurnLatency } from "../components/VoicePanel";
import { TaskPanel } from "../components/TaskPanel";
import { MissionControl } from "../components/MissionControl";
import { LatencyHud, ProviderStrip, useProviders } from "../components/StatusBits";

export interface Scenario { id: string; title: string; language: LangCode; prompt: string; fixture?: { name: string; label: string } | null }

export function useLanguages() {
  const [langs, setLangs] = useState<Language[]>([]);
  const [pending, setPending] = useState<{ code: string; english: string }[]>([]);
  useEffect(() => {
    api.languages().then((r) => { setLangs(r.verified); setPending(r.pending); }).catch(() => undefined);
  }, []);
  return { langs, pending };
}

export default function Workspace({ scenario }: { scenario?: Scenario }) {
  const { settings, update } = useSettings();
  const s = useSession();
  const { langs, pending } = useLanguages();
  const { providers, usage } = useProviders();
  const [latency, setLatency] = useState<TurnLatency>({});
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const [ttsError, setTtsError] = useState<string | null>(null);
  const [mobileBrowser, setMobileBrowser] = useState(false);
  const turnStarted = useRef(0);
  const spoken = useRef<Set<string>>(new Set());
  const language: LangCode = scenario?.language ?? settings.language;
  const voice = langs.find((l) => l.code === language)?.voices.includes(settings.voice ?? "") ? settings.voice : null;

  const onLatency = useCallback((l: Partial<TurnLatency>, reset?: boolean) => setLatency((p) => (reset ? { ...l } : { ...p, ...l })), []);

  const { start } = s;
  const startSession = useCallback(async () => {
    speaker.stop();
    spoken.current = new Set();
    setLatency({});
    await start(language, settings.retainHistory);
  }, [start, language, settings.retainHistory]);

  // A new session whenever the language (or judge scenario) changes.
  useEffect(() => { void startSession(); }, [startSession, scenario?.id]);

  useEffect(() => speaker.onChange((_, id) => setSpeakingId(id)), []);
  useEffect(() => () => speaker.stop(), []);

  // Speak every new assistant message (same text as displayed). Measure time-to-first-audio for the HUD.
  const messages = s.session?.messages;
  const sid = s.session?.id;
  useEffect(() => {
    if (!messages || !sid) return;
    const fresh = messages.filter((m) => m.role === "assistant" && !spoken.current.has(m.id));
    fresh.forEach((m) => spoken.current.add(m.id));
    if (!settings.autoplay || !fresh.length) return;
    fresh.forEach((m, i) => {
      speaker.speak({ id: m.id, text: m.text, language: m.lang, voice: voice ?? undefined, sessionId: sid, purpose: m.kind === "question" ? "clarification" : m.kind })
        .then((r) => {
          setTtsError(null);
          if (r && i === 0 && turnStarted.current) {
            onLatency({ ttfaMs: r.ttfaMs, ttsServerMs: r.serverMs, ttsCache: r.cache, sendToAudioMs: Math.round(r.playingAt - turnStarted.current) });
            turnStarted.current = 0;
          }
        })
        .catch((e: Error) => setTtsError(e.message || "Voice playback failed"));
    });
  }, [messages, sid, settings.autoplay, voice, onLatency]);

  return (
    <div className="mx-auto max-w-[1500px] px-4 py-4">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm font-semibold">
          Language
          <select value={language} disabled={!!scenario} onChange={(e) => update({ language: e.target.value as LangCode, voice: null })}
            className="rounded-md border border-line bg-white px-3 py-2 text-base">
            {langs.map((l) => <option key={l.code} value={l.code}>{l.native} · {l.english}</option>)}
          </select>
        </label>
        {pending.length > 0 && (
          <span className="text-xs text-ink-faint">Not yet verified with this key: {pending.map((p) => p.english).join(", ")}</span>
        )}
        <div className="ml-auto flex flex-wrap gap-2">
          <button className="btn-ghost" onClick={() => void startSession()}><Plus className="h-4 w-4" aria-hidden />{ui("newTask", language)}</button>
          <button className="btn-ghost" onClick={() => void s.remove().then(startSession)} title="Delete this session's events, screenshots and history"><Trash2 className="h-4 w-4" aria-hidden />Delete session</button>
        </div>
      </div>
      <div className="mb-3"><ProviderStrip providers={providers} usage={usage} /></div>
      {providers && !providers.reasoning.is_ai && (
        <p className="mb-3 rounded-md border border-line bg-white px-3 py-2 text-sm">
          <b>Rules fallback (no AI model)</b> is interpreting requests — a limited keyword engine.
        </p>
      )}
      {s.error && <div role="alert" className="mb-3 rounded-md bg-danger-light px-3 py-2 text-sm text-danger">{s.error}</div>}
      {ttsError && (
        <div role="alert" className="mb-3 flex items-center gap-3 rounded-md bg-saffron-light px-3 py-2 text-sm">
          Voice is unavailable right now ({ttsError}). Messages are shown as text.
          <button className="btn-ghost text-xs" onClick={() => setTtsError(null)}><RotateCcw className="h-3 w-3" aria-hidden />Dismiss</button>
        </div>
      )}
      {s.ws === "closed" && s.session && <p className="mb-3 text-xs text-ink-faint">Reconnecting live updates…</p>}

      {scenario && (
        <div className="mb-3 rounded-lg border border-saffron bg-saffron-light/50 p-3 text-sm">
          <b>{scenario.title}.</b> Say (or use the fixture): <span lang={scenario.language} className="font-medium">“{scenario.prompt}”</span>
        </div>
      )}

      <div className={`grid gap-4 ${settings.voiceOnly ? "lg:grid-cols-[1fr_1fr]" : "lg:grid-cols-[minmax(320px,1fr)_minmax(300px,0.9fr)_minmax(360px,1.15fr)]"}`}>
        <VoicePanel s={s} language={language} voice={voice} voiceOnly={settings.voiceOnly} speakingId={speakingId} onLatency={onLatency}
          turnStarted={turnStarted} fixture={scenario?.fixture ?? null} />
        {!settings.voiceOnly && <TaskPanel s={s} language={language} voice={voice} />}
        <div className="lg:hidden">
          <button className="btn-ghost w-full justify-center" aria-expanded={mobileBrowser} onClick={() => setMobileBrowser((o) => !o)}>
            {mobileBrowser ? "Hide" : "Show"} browser preview
          </button>
        </div>
        <div className={`${mobileBrowser ? "" : "hidden"} lg:block`}>
          <MissionControl s={s} language={language} compact={settings.voiceOnly} />
        </div>
        {settings.voiceOnly && <TaskPanel s={s} language={language} voice={voice} />}
      </div>
      <div className="mt-4"><LatencyHud l={latency} /></div>
    </div>
  );
}
