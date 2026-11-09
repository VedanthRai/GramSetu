"""AI reasoning providers. Output is schema-constrained JSON validated by Pydantic; one retry, then rephrase."""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.logging import get_logger, sanitize
from app.schemas.contracts import ReasoningOutput
from app.security.guards import redact_for_model
from app.services.reasoning.base import DialogueContext, ReasoningFailure
from app.services.speech.base import ProviderHealth

log = get_logger("gramsetu.reasoning")
PROMPT_VERSION = "interpret_v1"
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / f"{PROMPT_VERSION}.md").read_text(encoding="utf-8")


def _schema() -> dict:
    s = ReasoningOutput.model_json_schema()
    return s


def build_user_message(text: str, ctx: DialogueContext) -> str:
    """Minimum necessary data: no secrets, digit runs redacted, only field NAMES of known values."""
    return (
        f"<today>{ctx.today_iso} ({ctx.weekday}), timezone Asia/Kolkata</today>\n"
        f"<ui_language>{ctx.language}</ui_language>\n"
        f"<current_task>{ctx.current_intent or 'none'}</current_task>\n"
        f"<question_just_asked_for_field>{ctx.expected_field or 'none'}</question_just_asked_for_field>\n"
        f"<fields_already_known>{', '.join(ctx.known_field_names) or 'none'}</fields_already_known>\n"
        f"<offered_options>{json.dumps(ctx.offered_options, ensure_ascii=False)}</offered_options>\n"
        f"<allowed_values>{json.dumps(ctx.allowed_values, ensure_ascii=False)}</allowed_values>\n"
        f"<user_text>{redact_for_model(text)[:1000]}</user_text>"
    )


class _LLMBase:
    is_ai = True
    label = ""

    def __init__(self, provider: str, model: str, configured: bool) -> None:
        self.health = ProviderHealth(name=self.label, kind="reasoning", configured=configured,
                                     extra={"provider": provider, "model": model, "prompt_version": PROMPT_VERSION})
        self.model = model

    async def _call(self, user_msg: str, feedback: str | None) -> str:
        raise NotImplementedError

    async def interpret(self, text: str, ctx: DialogueContext) -> ReasoningOutput:
        if not self.health.configured:
            raise ReasoningFailure("Reasoning provider is not configured")
        msg = build_user_message(text, ctx)
        feedback = None
        for attempt in range(2):
            t0 = time.perf_counter()
            try:
                raw = await self._call(msg, feedback)
            except Exception as e:  # network / API errors: surfaced, not hidden
                self.health.fail(f"{type(e).__name__}: {e}")
                raise ReasoningFailure(f"Reasoning call failed: {type(e).__name__}") from e
            self.health.ok(int((time.perf_counter() - t0) * 1000))
            try:
                return ReasoningOutput.model_validate_json(raw)
            except ValidationError as e:
                feedback = sanitize(str(e))[:800]
                log.warning("Reasoning output failed validation (attempt %d)", attempt + 1)
        raise ReasoningFailure("Model output failed schema validation twice")


class OpenAICompatibleReasoner(_LLMBase):
    label = "OpenAI-compatible endpoint"

    def __init__(self) -> None:
        s = get_settings()
        super().__init__("openai_compatible", s.reasoning_model,
                         bool(s.reasoning_base_url and s.reasoning_api_key and s.reasoning_model))
        self.base_url, self.key = s.reasoning_base_url.rstrip("/"), s.reasoning_api_key

    async def _call(self, user_msg: str, feedback: str | None) -> str:
        content = user_msg + (f"\n<previous_output_validation_error>{feedback}</previous_output_validation_error>" if feedback else "")
        body = {"model": self.model, "temperature": 0,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT + "\nReply with JSON only, matching this schema: "
                              + json.dumps(_schema())}, {"role": "user", "content": content}],
                "response_format": {"type": "json_object"}}
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(f"{self.base_url}/chat/completions", json=body,
                             headers={"Authorization": f"Bearer {self.key}"})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
