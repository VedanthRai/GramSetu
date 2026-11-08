from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.schemas.contracts import ReasoningOutput
from app.services.speech.base import ProviderHealth


@dataclass
class DialogueContext:
    """Minimum necessary context for interpretation. Contains no secrets and no raw ID numbers."""

    language: str
    today_iso: str
    weekday: str
    current_intent: str | None = None
    expected_field: str | None = None
    known_field_names: list[str] = field(default_factory=list)
    offered_options: dict[str, list[str]] = field(default_factory=dict)  # e.g. {"slot_time": ["09:30","10:00"]}
    allowed_values: dict[str, list[str]] = field(default_factory=dict)


class ReasoningProvider(Protocol):
    health: ProviderHealth
    label: str
    is_ai: bool

    async def interpret(self, text: str, ctx: DialogueContext) -> ReasoningOutput: ...


class ReasoningFailure(RuntimeError):
    pass
