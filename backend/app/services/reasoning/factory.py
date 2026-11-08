from __future__ import annotations

from app.core.config import get_settings
from app.services.reasoning.llm import AnthropicReasoner, OpenAICompatibleReasoner
from app.services.reasoning.rules import RulesReasoner


def build_reasoner():
    p = get_settings().reasoning_provider.strip().lower()
    if p == "anthropic":
        return AnthropicReasoner()
    if p == "openai_compatible":
        return OpenAICompatibleReasoner()
    return RulesReasoner()
