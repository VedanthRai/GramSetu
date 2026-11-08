"""Application settings, loaded from the repo-root .env. Secrets are never logged."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(REPO_ROOT / ".env"), extra="ignore")

    gnani_api_key: str = ""
    gnani_base_url: str = "https://api.vachana.ai"
    gnani_stt_model: str = ""  # empty = Prisma v2.5 (default); "prisma-v3.0" optional
    gnani_tts_model: str = "timbre-v2.5"
    gnani_fixture_mode: bool = False
    daily_gnani_request_limit: int = 150

    reasoning_provider: str = "rules"  # anthropic | openai_compatible | rules
    anthropic_api_key: str = ""
    reasoning_model: str = ""
    reasoning_base_url: str = ""
    reasoning_api_key: str = ""

    app_mode: str = "demo"
    timezone: str = "Asia/Kolkata"
    retain_transcripts: bool = False
    app_origin: str = "http://127.0.0.1:8000"
    browser_headless: bool = True
    db_path: str = Field(default=str(DATA_DIR / "gramsetu.db"))

    @property
    def effective_reasoning_model(self) -> str:
        if self.reasoning_model:
            return self.reasoning_model
        return "claude-opus-5-5" if self.reasoning_provider == "anthropic" else ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
