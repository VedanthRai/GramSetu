"""Gnani (Vachana) Prisma STT + Timbre TTS smoke test.

Credit-aware by design. Default ("minimal") mode makes exactly:
  1 Timbre TTS call (Hindi)  -> saves WAV fixture
  1 Prisma STT call on that WAV -> checks the round trip
Use --langs to expand incrementally, e.g. --langs kn-IN ta-IN en-IN (2 calls per language),
and --voices 2 to try a second voice per language (1 extra TTS call each).

Endpoints/headers come from https://docs.gnani.ai/api (read 2026-11-08):
  POST {base}/api/v1/tts/inference  (JSON, header X-API-Key-ID) -> raw audio bytes
  POST {base}/stt/v3                (multipart: audio_file, language_code) -> JSON
The key is read from the environment / .env and never printed.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import wave
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.stdout.reconfigure(encoding="utf-8")

BASE = os.environ.get("GNANI_BASE_URL") or "https://api.vachana.ai"
KEY = os.environ.get("GNANI_API_KEY", "")

PHRASES = {
    "hi-IN": ("मैं किसान हूँ। मेरे पास दो एकड़ जमीन है।", ["Nalini", "Deepak"]),
    "kn-IN": ("ನನಗೆ ನಾಳೆ ಬೆಳಿಗ್ಗೆ ವೈದ್ಯರ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬೇಕು.", ["Saanvi", "Kavin"]),
    "ta-IN": ("எனக்கு நாளை காலை மருத்துவர் சந்திப்பு வேண்டும்.", ["Asmita", "Trisha"]),
    "en-IN": ("I need a doctor's appointment tomorrow morning.", ["Kaveri", "Pranav"]),
}

calls: list[dict] = []


def tts(client: httpx.Client, text: str, lang: str, voice: str) -> bytes | None:
    body = {
        "text": text, "voice": voice, "model": "timbre-v2.5", "language": lang, "speed": 1.0,
        "audio_config": {"sample_rate": 16000, "num_channels": 1, "sample_width": 2,
                         "encoding": "linear_pcm", "container": "wav"},
    }
    t0 = time.perf_counter()
    r = client.post(f"{BASE}/api/v1/tts/inference", json=body, headers={"X-API-Key-ID": KEY})
    dt = time.perf_counter() - t0
    rec = {"api": "tts", "lang": lang, "voice": voice, "status": r.status_code, "latency_s": round(dt, 3),
           "content_type": r.headers.get("content-type"), "bytes": len(r.content), "chars": len(text),
           "headers_of_interest": {k: v for k, v in r.headers.items()
                                   if any(s in k.lower() for s in ("credit", "usage", "limit", "remaining", "quota"))}}
    if r.status_code == 200 and r.content[:4] == b"RIFF":
        with wave.open(io.BytesIO(r.content)) as w:
            sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        # Timbre's header declares a placeholder data length; compute duration from actual bytes.
        rec.update(sample_rate=sr, channels=ch, sample_width=sw,
                   duration_s=round((len(r.content) - 44) / (sr * ch * sw), 2),
                   header_declared_frames_bogus=True)
    else:
        rec["error_body"] = r.text[:300]
    calls.append(rec)
    print(json.dumps(rec, ensure_ascii=False))
    return r.content if r.status_code == 200 else None


def stt(client: httpx.Client, wav: bytes, lang: str, name: str) -> dict | None:
    t0 = time.perf_counter()
    r = client.post(f"{BASE}/stt/v3", headers={"X-API-Key-ID": KEY},
                    files={"audio_file": (name, wav, "audio/wav")}, data={"language_code": lang})
    dt = time.perf_counter() - t0
    rec = {"api": "stt", "lang": lang, "status": r.status_code, "latency_s": round(dt, 3),
           "headers_of_interest": {k: v for k, v in r.headers.items()
                                   if any(s in k.lower() for s in ("credit", "usage", "limit", "remaining", "quota"))}}
    try:
        body = r.json()
    except ValueError:
        body = {"raw": r.text[:300]}
    rec["response"] = body
    calls.append(rec)
    print(json.dumps(rec, ensure_ascii=False))
    return body if r.status_code == 200 else None


def update_capabilities(run_calls: list[dict]) -> None:
    """Mark a language verified only when BOTH a Timbre synthesis and a non-empty Prisma transcript succeeded."""
    cap_file = ROOT / "backend" / "app" / "services" / "speech" / "verified_capabilities.json"
    caps = json.loads(cap_file.read_text(encoding="utf-8"))
    for lang, c in caps["languages"].items():
        tts_ok = [x["voice"] for x in run_calls if x["api"] == "tts" and x["lang"] == lang and x["status"] == 200]
        stt_ok = any(x["api"] == "stt" and x["lang"] == lang and x["status"] == 200
                     and (x["response"].get("transcript") or "").strip() for x in run_calls)
        if tts_ok:
            c["tts"] = "verified"
            c["voices_verified"] = sorted(set(c.get("voices_verified", [])) | set(tts_ok))
        if stt_ok:
            c["stt"] = "verified"
    cap_file.write_text(json.dumps(caps, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Capability table updated:", {k: (v["stt"], v["tts"], v["voices_verified"]) for k, v in caps["languages"].items()})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="*", default=["hi-IN"])
    ap.add_argument("--voices", type=int, default=1)
    ap.add_argument("--stt-only", action="store_true", help="reuse saved Timbre fixtures, no TTS calls")
    args = ap.parse_args()
    if not KEY:
        print("GNANI_API_KEY missing", file=sys.stderr)
        return 2
    out_dir = ROOT / "fixtures" / "audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60) as client:
        for lang in args.langs:
            text, voices = PHRASES[lang]
            first_wav = None
            if args.stt_only:
                saved = sorted(out_dir.glob(f"timbre_{lang}_*.wav"))
                first_wav = saved[0].read_bytes() if saved else None
            for v in ([] if args.stt_only else voices[: args.voices]):
                wav = tts(client, text, lang, v)
                if wav and first_wav is None:
                    first_wav = wav
                    (out_dir / f"timbre_{lang}_{v}.wav").write_bytes(wav)
            if first_wav:
                stt(client, first_wav, lang, f"timbre_{lang}.wav")
    update_capabilities(calls)
    report = ROOT / "docs" / "smoke_test_result.json"
    prev = json.loads(report.read_text(encoding="utf-8")) if report.exists() else []
    prev.append({"run_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "calls": calls})
    report.write_text(json.dumps(prev, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRequests made this run: {len(calls)} (TTS {sum(c['api']=='tts' for c in calls)}, "
          f"STT {sum(c['api']=='stt' for c in calls)})")
    print("Usage/credit info in responses:",
          [c["headers_of_interest"] for c in calls if c["headers_of_interest"]] or "none returned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
