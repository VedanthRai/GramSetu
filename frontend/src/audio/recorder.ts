// Microphone capture via Web Audio (started only after an explicit click). Produces 16 kHz mono WAV.
import { encodeWav, mergeChunks, resample, rms, TARGET_RATE, toMono } from "./wav";

export const MAX_RECORD_SECONDS = 30; // Prisma REST limit (docs.gnani.ai: "Maximum duration: 30 seconds")
export const MIN_RECORD_SECONDS = 0.4;

const WORKLET = `
class Tap extends AudioWorkletProcessor {
  process(inputs) { const ch = inputs[0] && inputs[0][0]; if (ch) this.port.postMessage(ch.slice(0)); return true; }
}
registerProcessor("gs-tap", Tap);`;

export interface Recording { wav: Blob; seconds: number; level: number }

export class MicRecorder {
  private ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private node: AudioWorkletNode | null = null;
  private chunks: Float32Array[] = [];
  analyser: AnalyserNode | null = null;
  startedAt = 0;

  async start(): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    this.ctx = new AudioContext();
    const url = URL.createObjectURL(new Blob([WORKLET], { type: "application/javascript" }));
    await this.ctx.audioWorklet.addModule(url);
    URL.revokeObjectURL(url);
    const src = this.ctx.createMediaStreamSource(this.stream);
    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 512;
    this.node = new AudioWorkletNode(this.ctx, "gs-tap");
    this.chunks = [];
    this.node.port.onmessage = (e: MessageEvent<Float32Array>) => this.chunks.push(e.data);
    src.connect(this.analyser);
    src.connect(this.node);
    this.startedAt = performance.now();
  }

  async stop(): Promise<Recording> {
    const rate = this.ctx?.sampleRate ?? TARGET_RATE;
    this.node?.port.close();
    this.stream?.getTracks().forEach((t) => t.stop());
    await this.ctx?.close();
    const pcm = resample(mergeChunks(this.chunks), rate);
    this.chunks = [];
    this.ctx = null;
    this.stream = null;
    this.analyser = null;
    return { wav: new Blob([encodeWav(pcm)], { type: "audio/wav" }), seconds: pcm.length / TARGET_RATE, level: rms(pcm) };
  }

  abort(): void {
    this.stream?.getTracks().forEach((t) => t.stop());
    void this.ctx?.close();
    this.chunks = [];
  }
}

/** Convert an uploaded audio file (any format the browser can decode) to 16 kHz mono WAV. */
export async function fileToWav(file: Blob): Promise<Recording> {
  const ctx = new AudioContext();
  try {
    const decoded = await ctx.decodeAudioData(await file.arrayBuffer());
    const chans: Float32Array[] = [];
    for (let i = 0; i < decoded.numberOfChannels; i++) chans.push(decoded.getChannelData(i));
    const pcm = resample(toMono(chans), decoded.sampleRate);
    return { wav: new Blob([encodeWav(pcm)], { type: "audio/wav" }), seconds: pcm.length / TARGET_RATE, level: rms(pcm) };
  } finally {
    await ctx.close();
  }
}
