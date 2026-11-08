import { useEffect, useRef, useState } from "react";
import { FileAudio, Keyboard, Loader2, Mic, Pencil, Send, Square, Volume2, VolumeX, X } from "lucide-react";
import { api, ApiError, type LangCode, type Message } from "../lib/api";
import { fileToWav, MAX_RECORD_SECONDS, MicRecorder, MIN_RECORD_SECONDS, type Recording } from "../audio/recorder";
import { speaker } from "../audio/player";
import { ui } from "../lib/ui";
import type { SessionApi } from "../lib/useSession";
import { Badge, Card } from "./Layout";
import { Link } from "react-router-dom";

export type MicMode = "idle" | "explain" | "requesting" | "listening" | "transcribing" | "thinking";

export interface TurnLatency { recordingS?: number; prismaMs?: number; reasoningMs?: number; ttfaMs?: number; sendToAudioMs?: number; ttsServerMs?: number; ttsCache?: string }

interface Props {
  fixture?: { name: string; label: string } | null;
  s: SessionApi;
  language: LangCode;
  voice: string | null;
  voiceOnly: boolean;
  speakingId: string | null;
  onLatency: (l: Partial<TurnLatency>, reset?: boolean) => void;
  turnStarted: React.MutableRefObject<number>;
}

const BUSY = new Set(["EXECUTING", "VERIFYING", "AWAITING_USER_ACTION", "INTERPRETING"]);
const SILENCE_RMS = 0.004;

export function VoicePanel({ fixture, s, language, voice, voiceOnly, speakingId, onLatency, turnStarted }: Props) {
  const [mode, setMode] = useState<MicMode>("idle");
  const [draft, setDraft] = useState("");
  const [raw, setRaw] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [typing, setTyping] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [left, setLeft] = useState(MAX_RECORD_SECONDS);
  const [explained, setExplained] = useState(false);
  const rec = useRef<MicRecorder | null>(null);
  const canvas = useRef<HTMLCanvasElement | null>(null);
  const timer = useRef<number | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const session = s.session;
  const busy = session ? BUSY.has(session.state) : true;

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [session?.messages.length]);

  useEffect(() => () => { rec.current?.abort(); if (timer.current) window.clearInterval(timer.current); }, []);

  const drawWave = () => {
    const a = rec.current?.analyser;
    const c = canvas.current;
    if (!a || !c) return;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    const data = new Uint8Array(a.fftSize);
    const loop = () => {
      if (!rec.current?.analyser) return;
      a.getByteTimeDomainData(data);
      ctx.clearRect(0, 0, c.width, c.height);
      ctx.lineWidth = 3;
      ctx.strokeStyle = "#d9771f";
      ctx.beginPath();
      for (let i = 0; i < data.length; i++) {
        const x = (i / data.length) * c.width;
        const y = (data[i] / 255) * c.height;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      requestAnimationFrame(loop);
    };
    loop();
  };

  const startRecording = async () => {
    setErr(null);
    speaker.stop();
    setMode("requesting");
    try {
      rec.current = new MicRecorder();
      await rec.current.start();
    } catch {
      setMode("idle");
      setErr("Microphone permission was not given. You can type instead, or allow the microphone in your browser settings.");
      return;
    }
    setMode("listening");
    onLatency({}, true);
    setLeft(MAX_RECORD_SECONDS);
    drawWave();
    timer.current = window.setInterval(() => {
      const elapsed = (performance.now() - (rec.current?.startedAt ?? 0)) / 1000;
      const remaining = Math.max(0, Math.ceil(MAX_RECORD_SECONDS - elapsed));
      setLeft(remaining);
      if (remaining <= 0) void stopRecording();
    }, 250);
  };

  const transcribe = async (r: Recording) => {
    if (r.seconds < MIN_RECORD_SECONDS) {
      setMode("idle");
      setErr("That was too short. Hold on a moment longer and speak a full sentence.");
      return;
    }
    if (r.seconds > MAX_RECORD_SECONDS + 0.5) {
      setMode("idle");
      setErr(`Recordings must be ${MAX_RECORD_SECONDS} seconds or shorter.`);
      return;
    }
    if (r.level < SILENCE_RMS) {
      setMode("idle");
      setErr("We could not hear any speech. Please speak closer to the microphone.");
      return;
    }
    setMode("transcribing");
    onLatency({ recordingS: Math.round(r.seconds * 10) / 10 });
    try {
      const t = await api.transcribe(r.wav, language, session?.id);
      onLatency({ prismaMs: t.latency_ms });
      setDraft(t.transcript);
      setRaw(t.transcript);
      setEditing(false);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Transcription failed. Please try again.");
    } finally {
      setMode("idle");
    }
  };

  const stopRecording = async () => {
    if (timer.current) window.clearInterval(timer.current);
    timer.current = null;
    if (!rec.current) return;
    const r = await rec.current.stop();
    rec.current = null;
    await transcribe(r);
  };

  const onMic = () => {
    if (mode === "listening") return void stopRecording();
    if (!explained) return setMode("explain");
    void startRecording();
  };

  const onUpload = async (f: File | undefined) => {
    if (!f) return;
    setErr(null);
    onLatency({}, true);
    try {
      await transcribe(await fileToWav(f));
    } catch {
      setErr("That file could not be read as audio.");
    }
  };

  const send = async (text: string, rawText?: string | null, choice?: { field: string; value: string }) => {
    if (!text.trim()) return;
    turnStarted.current = performance.now(); // machine time starts when you send (your review time is excluded)
    setMode("thinking");
    setDraft("");
    setRaw(null);
    setTyping(false);
    const r = await s.turn(text.trim(), rawText && rawText !== text ? rawText : undefined, choice);
    setMode("idle");
    if (r?.session.last_turn?.reasoning_ms !== undefined) onLatency({ reasoningMs: r.session.last_turn.reasoning_ms });
  };

  const micLabel = mode === "listening" ? ui("tapToSpeak", language) : ui("speak", language);
  const status =
    mode === "listening" ? `${ui("listening", language)} ${left}${ui("secondsLeft", language)}`
      : mode === "transcribing" ? ui("transcribing", language)
        : mode === "thinking" || session?.state === "INTERPRETING" ? ui("thinking", language)
          : busy ? ui("executing", language)
            : speakingId ? ui("speaking", language) : ui("ready", language);

  return (
    <Card id="voice-panel" title="Voice" className="flex min-h-0 flex-col" action={<Badge tone="saffron">Prisma · Timbre</Badge>}>
      <div ref={listRef} className="max-h-[62vh] min-h-[220px] flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite" aria-label="Conversation">
        {session?.messages.map((m) => (
          <MessageBubble key={m.id} m={m} voiceOnly={voiceOnly} speaking={speakingId === m.id}
            onReplay={() => speaker.speak({ id: m.id, text: m.text, language: m.lang, voice: voice ?? undefined, sessionId: session.id, purpose: "replay" }).catch(() => undefined)}
            onChoice={(c) => send(c.label, null, { field: m.field ?? "", value: c.value })}
            choicesActive={m.id === [...session.messages].reverse().find((x) => x.role === "assistant")?.id && !busy} />
        ))}
      </div>

      <div className="border-t border-line px-4 py-4">
        {(draft || editing) && (
          <div className="mb-3 rounded-lg border border-saffron/50 bg-saffron-light/40 p-3">
            <div className="mb-1 flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-saffron-dark">
              <span>Transcript — check before sending</span>
              {raw && raw !== draft && <span className="normal-case text-ink-soft">edited</span>}
            </div>
            {editing ? (
              <textarea aria-label="Edit transcript" value={draft} onChange={(e) => setDraft(e.target.value)} rows={3}
                className="w-full rounded-md border border-line bg-white p-2 text-lg" />
            ) : (
              <p className="text-lg leading-relaxed" lang={language} data-testid="transcript">{draft}</p>
            )}
            <div className="mt-2 flex flex-wrap gap-2">
              <button className="btn-primary" onClick={() => send(draft, raw)}><Send className="h-4 w-4" aria-hidden />{ui("send", language)}</button>
              <button className="btn-ghost" onClick={() => setEditing((e) => !e)}><Pencil className="h-4 w-4" aria-hidden />{ui("edit", language)}</button>
              <button className="btn-ghost" onClick={() => { setDraft(""); setRaw(null); setEditing(false); }} aria-label="Discard transcript"><X className="h-4 w-4" aria-hidden /></button>
            </div>
          </div>
        )}

        {err && <div role="alert" className="mb-3 rounded-md bg-danger-light px-3 py-2 text-sm text-danger">{err}</div>}

        {mode === "explain" && (
          <div className="mb-3 rounded-lg border border-line bg-white p-3 text-sm">
            <p className="font-semibold">Before you speak</p>
            <p className="mt-1 text-ink-soft">GramSetu listens only while the button is red, for at most {MAX_RECORD_SECONDS} seconds. Your audio is sent to Gnani Prisma to be written down and is not stored by GramSetu. Do not speak passwords or one-time codes.</p>
            <div className="mt-3 flex gap-2">
              <button className="btn-primary" onClick={() => { setExplained(true); void startRecording(); }}><Mic className="h-4 w-4" aria-hidden />Allow microphone and start</button>
              <button className="btn-ghost" onClick={() => setMode("idle")}>Not now</button>
            </div>
          </div>
        )}

        <div className={`flex items-center gap-4 ${voiceOnly ? "flex-col" : ""}`}>
          <button onClick={onMic} disabled={!session || busy || mode === "transcribing" || mode === "requesting" || mode === "thinking"}
            aria-pressed={mode === "listening"} aria-label={micLabel}
            className={`relative grid shrink-0 place-items-center rounded-full text-white shadow-lg transition focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-saffron disabled:cursor-not-allowed disabled:opacity-40 ${voiceOnly ? "h-40 w-40" : "h-20 w-20"} ${mode === "listening" ? "bg-danger motion-safe:animate-pulse" : "bg-ink hover:bg-ink/90"}`}>
            {mode === "transcribing" || mode === "thinking" || mode === "requesting" ? <Loader2 className={`${voiceOnly ? "h-16 w-16" : "h-8 w-8"} animate-spin`} aria-hidden />
              : mode === "listening" ? <Square className={voiceOnly ? "h-14 w-14" : "h-7 w-7"} aria-hidden /> : <Mic className={voiceOnly ? "h-16 w-16" : "h-8 w-8"} aria-hidden />}
          </button>
          <div className="min-w-0 flex-1 text-center sm:text-left">
            <p className={`font-semibold ${voiceOnly ? "text-2xl" : "text-base"}`} role="status">{status}</p>
            <canvas ref={canvas} width={320} height={44} className={`mt-1 h-11 w-full max-w-xs ${mode === "listening" ? "" : "hidden"}`} aria-hidden />
            {!voiceOnly && mode !== "listening" && <p className="text-xs text-ink-soft">Speak in your language. You will see the words before anything happens.</p>}
          </div>
          {speakingId && (
            <button className="btn-ghost" onClick={() => speaker.stop()} aria-label="Stop speaking"><VolumeX className="h-5 w-5" aria-hidden />{ui("stop", language)}</button>
          )}
        </div>

        {fixture && (
          <button className="btn-ghost mt-3 w-full justify-center border-dashed" disabled={busy || mode !== "idle"}
            onClick={async () => {
              const r = await fetch(`/api/fixtures/audio/${fixture.name}`);
              if (!r.ok) return setErr("Fixture audio missing.");
              onLatency({}, true);
              await transcribe(await fileToWav(await r.blob()));
            }}>
            <FileAudio className="h-4 w-4" aria-hidden />Use labelled audio fixture (synthetic, Timbre-generated) → live Prisma
          </button>
        )}
        {!voiceOnly && (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
            <button className="btn-ghost" onClick={() => setTyping((t) => !t)} aria-expanded={typing}><Keyboard className="h-4 w-4" aria-hidden />{ui("typeInstead", language)}</button>
            <label className="btn-ghost cursor-pointer">
              <FileAudio className="h-4 w-4" aria-hidden />{ui("upload", language)}
              <input type="file" accept="audio/*" className="sr-only" onChange={(e) => { void onUpload(e.target.files?.[0]); e.target.value = ""; }} />
            </label>
          </div>
        )}
        {typing && (
          <form className="mt-2 flex gap-2" onSubmit={(e) => { e.preventDefault(); const f = new FormData(e.currentTarget); void send(String(f.get("t") ?? "")); }}>
            <label htmlFor="typed" className="sr-only">Type your message</label>
            <input id="typed" name="t" autoComplete="off" className="min-w-0 flex-1 rounded-md border border-line bg-white px-3 py-2 text-lg" lang={language} placeholder="…" disabled={busy} />
            <button className="btn-primary" disabled={busy}><Send className="h-4 w-4" aria-hidden />{ui("send", language)}</button>
          </form>
        )}
      </div>
    </Card>
  );
}

function MessageBubble({ m, onReplay, onChoice, choicesActive, speaking, voiceOnly }: {
  m: Message; onReplay: () => void; onChoice: (c: { value: string; label: string }) => void; choicesActive: boolean; speaking: boolean; voiceOnly: boolean;
}) {
  const mine = m.role === "user";
  const tone = m.kind === "emergency" ? "border-danger bg-danger-light" : m.kind === "warning" ? "border-saffron bg-saffron-light"
    : m.kind === "success" ? "border-verified bg-verified-light" : m.kind === "error" ? "border-danger/50 bg-danger-light/60" : "border-line bg-white";
  return (
    <div className={`flex ${mine ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[92%] rounded-2xl border px-4 py-3 ${mine ? "rounded-br-sm border-ink bg-ink text-white" : `rounded-bl-sm ${tone}`} ${speaking ? "ring-2 ring-saffron" : ""}`}>
        <p lang={m.lang} className={`whitespace-pre-line leading-relaxed ${voiceOnly ? "text-xl" : "text-[15px]"}`}>{m.text}</p>
        {m.raw_transcript && <p className="mt-1 text-xs opacity-70">Prisma heard: “{m.raw_transcript}”</p>}
        {m.kind === "guidance" && m.source_url && (
          <Link to="/sources" className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-saffron-dark underline">
            Source: official PM-KISAN website, retrieved 8 Nov 2026 · view statements
          </Link>
        )}
        {m.completed_steps && m.completed_steps.length > 0 && (
          <details className="mt-2 text-xs"><summary className="cursor-pointer font-semibold">What already happened on the portal</summary>
            <ul className="mt-1 list-disc pl-4">{m.completed_steps.map((x, i) => <li key={i}>{x}</li>)}</ul></details>
        )}
        {m.choices && m.choices.length > 0 && choicesActive && (
          <div className="mt-3 flex flex-wrap gap-2">
            {m.choices.map((c) => (
              <button key={c.value} onClick={() => onChoice(c)} lang={m.lang}
                className={`rounded-full border border-ink/20 bg-white font-medium text-ink hover:border-saffron hover:bg-saffron-light ${voiceOnly ? "px-5 py-3 text-lg" : "px-3 py-1.5 text-sm"}`}>{c.label}</button>
            ))}
          </div>
        )}
        {!mine && (
          <button onClick={onReplay} className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-ink-soft hover:text-ink" aria-label="Replay this message">
            <Volume2 className="h-3.5 w-3.5" aria-hidden /> Replay
          </button>
        )}
      </div>
    </div>
  );
}
