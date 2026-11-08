"""Gnani Prisma (STT) and Timbre (TTS) over direct HTTP, per https://docs.gnani.ai/api (read 2026-11-08).

Why direct HTTP rather than the `gnani-vachana` SDK: the SDK still defaults TTS to the deprecated
timbre-v2.0 (docs warn about this), and two plain endpoints are simpler to audit, cache and meter.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time

import httpx

from app.core.config import DATA_DIR, get_settings
from app.core.logging import get_logger, sanitize
from app.db.database import db, now_iso
from app.services.speech.base import ProviderHealth, SpeechAudio, SpeechError, Transcript, load_capabilities
from app.services.speech.wav import normalise_wav, parse_wav
from app.services.usage import guard

log = get_logger("gramsetu.gnani")

# Gnani documents "Only 1 active request is allowed at a time" (429 RATE_LIMITED); serialise all calls.
_gnani_lock = asyncio.Lock()
TTS_CACHE_DIR = DATA_DIR / "tts_cache"
RETRYABLE = {429, 500, 503, 504}
MAX_RETRIES = 1  # credit protection: never more than one retry


def _err_message(r: httpx.Response) -> tuple[str, str]:
    try:
        body = r.json()
    except ValueError:
        return "HTTP_%d" % r.status_code, r.text[:200]
    if isinstance(body.get("detail"), dict):
        d = body["detail"]
        return d.get("error_code", f"HTTP_{r.status_code}"), d.get("message", "")
    if isinstance(body.get("error"), dict):
        return body["error"].get("type", f"HTTP_{r.status_code}"), body["error"].get("message", "")
    return body.get("code", f"HTTP_{r.status_code}"), str(body.get("message", ""))[:200]


async def _post_with_retry(client: httpx.AsyncClient, url: str, **kw) -> httpx.Response:
    attempt = 0
    while True:
        r = await client.post(url, **kw)
        if r.status_code in RETRYABLE and attempt < MAX_RETRIES:
            attempt += 1
            await asyncio.sleep(1.0)
            continue
        return r


class GnaniPrismaSTT:
    def __init__(self) -> None:
        s = get_settings()
        self.health = ProviderHealth(name="Gnani Prisma", kind="stt", configured=bool(s.gnani_api_key),
                                     extra={"model": s.gnani_stt_model or "prisma-v2.5", "mode": "REST (not streaming)",
                                            "fixture_mode": s.gnani_fixture_mode})

    async def transcribe(self, wav: bytes, language: str) -> Transcript:
        s = get_settings()
        info = parse_wav(wav)
        sha = hashlib.sha256(wav).hexdigest()
        if s.gnani_fixture_mode:
            with db() as c:
                row = c.execute("SELECT response FROM stt_fixtures WHERE audio_sha=? AND language=?",
                                (sha, language)).fetchone()
            if not row:
                raise SpeechError("NO_FIXTURE", "Fixture mode is on and no recorded Prisma response exists for this audio.", 409)
            body = json.loads(row["response"])
            guard.record("stt", cache_hits=1)
            return Transcript(text=body.get("transcript", ""), language=language, latency_ms=0,
                              model=body.get("model", "prisma"), audio_seconds=info.duration_s, source="fixture",
                              request_id=body.get("request_id"), literal=(body.get("output") or {}).get("literal"))
        if not s.gnani_api_key:
            raise SpeechError("NOT_CONFIGURED", "GNANI_API_KEY is not set.", 503)
        guard.check_allowed()
        data = {"language_code": language}
        if s.gnani_stt_model:
            data["model"] = s.gnani_stt_model
        async with _gnani_lock:
            t0 = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
                    r = await _post_with_retry(client, f"{s.gnani_base_url}/stt/v3",
                                               headers={"X-API-Key-ID": s.gnani_api_key},
                                               files={"audio_file": ("speech.wav", wav, "audio/wav")}, data=data)
            except httpx.HTTPError as e:
                guard.record("stt", calls=1, errors=1)
                self.health.fail(f"network: {type(e).__name__}")
                raise SpeechError("NETWORK", "Could not reach Gnani Prisma. Check your connection and try again.") from e
            latency = int((time.perf_counter() - t0) * 1000)
        guard.record("stt", calls=1, audio_seconds=info.duration_s, errors=0 if r.status_code == 200 else 1)
        if r.status_code != 200:
            code, msg = _err_message(r)
            self.health.fail(f"{r.status_code} {code}", reachable=True)
            log.warning("Prisma error %s %s", r.status_code, code)
            raise SpeechError(code, sanitize(msg) or "Prisma could not transcribe this audio.", 502 if r.status_code >= 500 else 400)
        body = r.json()
        self.health.ok(latency)
        with db() as c:
            c.execute("INSERT OR REPLACE INTO stt_fixtures VALUES (?,?,?,?)",
                      (sha, language, json.dumps(body, ensure_ascii=False), now_iso()))
        return Transcript(text=(body.get("transcript") or "").strip(), language=language, latency_ms=latency,
                          model=body.get("model", "prisma"), audio_seconds=info.duration_s, source="live",
                          request_id=body.get("request_id"), literal=(body.get("output") or {}).get("literal"))


class GnaniTimbreTTS:
    def __init__(self) -> None:
        s = get_settings()
        self.health = ProviderHealth(name="Gnani Timbre", kind="tts", configured=bool(s.gnani_api_key),
                                     extra={"model": s.gnani_tts_model, "mode": "REST (not streaming)",
                                            "fixture_mode": s.gnani_fixture_mode})

    @staticmethod
    def default_voice(language: str) -> str:
        caps = load_capabilities()["languages"].get(language)
        if not caps:
            raise SpeechError("UNSUPPORTED_LANGUAGE", f"{language} is not in the verified capability table.", 400)
        return caps["default_voice"]

    @staticmethod
    def allowed_voices(language: str) -> list[str]:
        caps = load_capabilities()["languages"].get(language) or {}
        return list(dict.fromkeys(caps.get("voices_verified", []) + caps.get("voices_documented", [])))

    async def synthesize(self, text: str, language: str, voice: str | None = None) -> SpeechAudio:
        s = get_settings()
        voice = voice or self.default_voice(language)
        if voice not in self.allowed_voices(language):
            raise SpeechError("UNSUPPORTED_VOICE", f"Voice {voice} is not listed for {language}.", 400)
        key = hashlib.sha256(json.dumps([text, language, voice, s.gnani_tts_model, 16000]).encode()).hexdigest()
        TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = TTS_CACHE_DIR / f"{key[:24]}.wav"  # short name: Windows MAX_PATH
        if path.exists():
            guard.record("tts", cache_hits=1)
            return SpeechAudio(path.read_bytes(), 0, True, voice, s.gnani_tts_model,
                               "fixture" if s.gnani_fixture_mode else "cache")
        if s.gnani_fixture_mode:
            raise SpeechError("NO_FIXTURE", "Fixture mode is on and this phrase has not been synthesised before.", 409)
        if not s.gnani_api_key:
            raise SpeechError("NOT_CONFIGURED", "GNANI_API_KEY is not set.", 503)
        guard.check_allowed()
        body = {"text": text, "voice": voice, "model": s.gnani_tts_model, "language": language, "speed": 1.0,
                "audio_config": {"sample_rate": 16000, "num_channels": 1, "sample_width": 2,
                                 "encoding": "linear_pcm", "container": "wav"}}
        async with _gnani_lock:
            t0 = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
                    r = await _post_with_retry(client, f"{s.gnani_base_url}/api/v1/tts/inference", json=body,
                                               headers={"X-API-Key-ID": s.gnani_api_key})
            except httpx.HTTPError as e:
                guard.record("tts", calls=1, errors=1)
                self.health.fail(f"network: {type(e).__name__}")
                raise SpeechError("NETWORK", "Could not reach Gnani Timbre.") from e
            latency = int((time.perf_counter() - t0) * 1000)
        guard.record("tts", calls=1, chars=len(text), errors=0 if r.status_code == 200 else 1)
        if r.status_code != 200 or r.content[:4] != b"RIFF":
            code, msg = _err_message(r)
            self.health.fail(f"{r.status_code} {code}", reachable=True)
            raise SpeechError(code, sanitize(msg) or "Timbre could not synthesise speech.")
        wav = normalise_wav(r.content)  # Timbre writes placeholder sizes in the WAV header
        path.write_bytes(wav)
        with db() as c:
            c.execute("INSERT OR REPLACE INTO tts_cache VALUES (?,?,?,?,?,?,?)",
                      (key, path.name, language, voice, s.gnani_tts_model, len(text), now_iso()))
        self.health.ok(latency)
        return SpeechAudio(wav, latency, False, voice, s.gnani_tts_model, "live")
