// Timbre playback with a sequential queue, stop, and measured time-to-first-audio.
import { ApiError, type LangCode } from "../lib/api";

export interface SpeakResult { ttfaMs: number; serverMs: number; cache: string; playingAt: number }
type Listener = (speaking: boolean, id: string | null) => void;

class Speaker {
  private audio: HTMLAudioElement | null = null;
  private queue: Promise<unknown> = Promise.resolve();
  private generation = 0;
  private listeners = new Set<Listener>();
  current: string | null = null;

  onChange(l: Listener): () => void {
    this.listeners.add(l);
    return () => this.listeners.delete(l);
  }

  private notify() {
    this.listeners.forEach((l) => l(this.current !== null, this.current));
  }

  stop(): void {
    this.generation++;
    this.audio?.pause();
    this.audio = null;
    this.current = null;
    this.notify();
  }

  speak(opts: { id: string; text: string; language: LangCode; voice?: string; sessionId?: string; purpose?: string }): Promise<SpeakResult | null> {
    const gen = this.generation;
    const run = async (): Promise<SpeakResult | null> => {
      if (gen !== this.generation) return null;
      const t0 = performance.now();
      const r = await fetch("/api/speech/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: opts.text, language: opts.language, voice: opts.voice, session_id: opts.sessionId, purpose: opts.purpose }),
      });
      if (!r.ok) {
        let msg = "Speech could not be played";
        try {
          const b = (await r.json()) as { detail?: { message?: string } };
          msg = b.detail?.message ?? msg;
        } catch { /* ignore */ }
        throw new ApiError(r.status, "TTS", msg);
      }
      const blob = await r.blob();
      if (gen !== this.generation) return null;
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      this.audio = audio;
      this.current = opts.id;
      this.notify();
      let playingAt = 0;
      const ttfa = await new Promise<number>((resolve, reject) => {
        audio.onplaying = () => { playingAt = performance.now(); resolve(playingAt - t0); };
        audio.onerror = () => reject(new ApiError(0, "PLAYBACK", "Audio playback failed"));
        audio.play().catch(reject);
      });
      await new Promise<void>((resolve) => {
        audio.onended = () => resolve();
        audio.onpause = () => resolve();
      });
      URL.revokeObjectURL(url);
      if (this.current === opts.id) {
        this.current = null;
        this.notify();
      }
      return { ttfaMs: Math.round(ttfa), serverMs: Number(r.headers.get("X-Latency-Ms") ?? 0), cache: r.headers.get("X-Cache") ?? "", playingAt };
    };
    const p = this.queue.then(run, run);
    this.queue = p.catch(() => undefined);
    return p;
  }
}

export const speaker = new Speaker();

export async function synthesizeBlob(text: string, language: LangCode, voice?: string): Promise<Blob> {
  const r = await fetch("/api/speech/synthesize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language, voice, purpose: "summary download" }),
  });
  if (!r.ok) throw new ApiError(r.status, "TTS", "Speech could not be generated");
  return r.blob();
}
