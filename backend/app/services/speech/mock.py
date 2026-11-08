"""Mock speech providers — for automated tests ONLY. Never wired up by the running app."""
from __future__ import annotations

from app.services.speech.base import ProviderHealth, SpeechAudio, Transcript
from app.services.speech.wav import build_wav, parse_wav


class MockSTT:
    def __init__(self, transcript: str = "") -> None:
        self.next_transcript = transcript
        self.health = ProviderHealth(name="Mock STT (tests only)", kind="stt", configured=True)

    async def transcribe(self, wav: bytes, language: str) -> Transcript:
        info = parse_wav(wav)
        return Transcript(self.next_transcript, language, 1, "mock", info.duration_s, "mock")


class MockTTS:
    def __init__(self) -> None:
        self.health = ProviderHealth(name="Mock TTS (tests only)", kind="tts", configured=True)
        self.calls: list[str] = []

    async def synthesize(self, text: str, language: str, voice: str | None = None) -> SpeechAudio:
        self.calls.append(text)
        return SpeechAudio(build_wav(b"\x00\x00" * 1600, 16000), 1, False, voice or "mock", "mock", "mock")
