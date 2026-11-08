import { describe, expect, it } from "vitest";
import { encodeWav, mergeChunks, resample, rms, toMono } from "./wav";

describe("wav encoding", () => {
  it("writes a canonical 16-bit mono PCM header", () => {
    const buf = encodeWav(new Float32Array(16000), 16000);
    const v = new DataView(buf);
    const str = (o: number) => String.fromCharCode(...new Uint8Array(buf, o, 4));
    expect(str(0)).toBe("RIFF");
    expect(str(8)).toBe("WAVE");
    expect(v.getUint16(20, true)).toBe(1);
    expect(v.getUint16(22, true)).toBe(1);
    expect(v.getUint32(24, true)).toBe(16000);
    expect(v.getUint16(34, true)).toBe(16);
    expect(v.getUint32(40, true)).toBe(32000);
    expect(buf.byteLength).toBe(44 + 32000);
  });

  it("clips samples outside [-1, 1]", () => {
    const v = new DataView(encodeWav(new Float32Array([2, -2]), 16000));
    expect(v.getInt16(44, true)).toBe(32767);
    expect(v.getInt16(46, true)).toBe(-32768);
  });
});

describe("resampling", () => {
  it("downsamples 48 kHz to 16 kHz with the right length", () => {
    const out = resample(new Float32Array(48000).fill(0.5), 48000, 16000);
    expect(out.length).toBe(16000);
    expect(out[100]).toBeCloseTo(0.5);
  });
  it("is a copy when rates match", () => {
    const a = new Float32Array([0.1, 0.2]);
    const b = resample(a, 16000, 16000);
    expect(Array.from(b)).toEqual(Array.from(a));
    expect(b).not.toBe(a);
  });
});

describe("helpers", () => {
  it("merges chunks in order", () => {
    expect(Array.from(mergeChunks([new Float32Array([1]), new Float32Array([2, 3])]))).toEqual([1, 2, 3]);
  });
  it("computes rms and detects silence", () => {
    expect(rms(new Float32Array(100))).toBe(0);
    expect(rms(new Float32Array([1, -1]))).toBeCloseTo(1);
  });
  it("averages channels to mono", () => {
    expect(Array.from(toMono([new Float32Array([1, 0]), new Float32Array([0, 1])]))).toEqual([0.5, 0.5]);
  });
});
