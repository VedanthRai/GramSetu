"""Process-wide provider singletons."""
from __future__ import annotations

from functools import lru_cache

from app.services.orchestrator import Orchestrator
from app.services.reasoning.factory import build_reasoner
from app.services.speech.gnani import GnaniPrismaSTT, GnaniTimbreTTS


class Providers:
    def __init__(self, stt=None, tts=None, reasoner=None) -> None:
        self.stt = stt or GnaniPrismaSTT()
        self.tts = tts or GnaniTimbreTTS()
        self.reasoner = reasoner or build_reasoner()
        self.orchestrator = Orchestrator(self.reasoner)


_override: Providers | None = None


@lru_cache
def _default() -> Providers:
    return Providers()


def providers() -> Providers:
    return _override or _default()


def set_providers(p: Providers | None) -> None:
    global _override
    _override = p
