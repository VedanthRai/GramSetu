"""Provider interfaces + shared health tracking."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from app.core.logging import sanitize

CAPABILITIES_FILE = Path(__file__).with_name("verified_capabilities.json")

LANGUAGE_NAMES = {
    "hi-IN": {"english": "Hindi", "native": "हिन्दी"},
    "kn-IN": {"english": "Kannada", "native": "ಕನ್ನಡ"},
    "ta-IN": {"english": "Tamil", "native": "தமிழ்"},
    "en-IN": {"english": "English (India)", "native": "English"},
}


def load_capabilities() -> dict:
    return json.loads(CAPABILITIES_FILE.read_text(encoding="utf-8"))


def verified_languages() -> list[dict]:
    caps = load_capabilities()["languages"]
    out = []
    for code, c in caps.items():
        if c.get("stt") == "verified" and c.get("tts") == "verified":
            out.append({"code": code, **LANGUAGE_NAMES.get(code, {"english": code, "native": code}),
                        "voices": c.get("voices_verified", []), "default_voice": c.get("default_voice")})
    return out


@dataclass
class ProviderHealth:
    name: str
    kind: str
    configured: bool = False
    reachable: bool | None = None  # None = not yet called
    last_latency_ms: int | None = None
    last_error: str | None = None
    last_called_at: float | None = None
    extra: dict = field(default_factory=dict)

    def ok(self, latency_ms: int) -> None:
        self.reachable, self.last_latency_ms, self.last_error = True, latency_ms, None
        self.last_called_at = time.time()

    def fail(self, err: str, reachable: bool | None = False) -> None:
        self.reachable, self.last_error = reachable, sanitize(err)[:200]
        self.last_called_at = time.time()

    def as_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "configured": self.configured, "reachable": self.reachable,
                "last_latency_ms": self.last_latency_ms, "last_error": self.last_error,
                "last_called_at": self.last_called_at, **self.extra}


class SpeechError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 502):
        super().__init__(message)
        self.code, self.status = code, status


@dataclass
class Transcript:
    text: str
    language: str
    latency_ms: int
    model: str
    audio_seconds: float
    source: str  # "live" | "fixture"
    request_id: str | None = None
    literal: str | None = None


@dataclass
class SpeechAudio:
    wav: bytes
    latency_ms: int
    cache_hit: bool
    voice: str
    model: str
    source: str  # "live" | "cache" | "fixture"


class SpeechToTextProvider(Protocol):
    health: ProviderHealth

    async def transcribe(self, wav: bytes, language: str) -> Transcript: ...


class TextToSpeechProvider(Protocol):
    health: ProviderHealth

    async def synthesize(self, text: str, language: str, voice: str | None = None) -> SpeechAudio: ...
