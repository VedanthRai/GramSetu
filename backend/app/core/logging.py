"""Sanitized logging: secrets, OTP-like digit runs and API keys are scrubbed before output."""
from __future__ import annotations

import logging
import re

from app.core.config import get_settings

_PATTERNS = [
    (re.compile(r"vach_[A-Za-z0-9_\-]{8,}"), "[REDACTED_KEY]"),
    (re.compile(r"sk-[A-Za-z0-9_\-]{8,}"), "[REDACTED_KEY]"),
    (re.compile(r"(?i)(otp|pin|password|passcode|cvv)\W{0,3}\d{3,8}"), r"\1 [REDACTED]"),
    (re.compile(r"\b\d{9,18}\b"), "[REDACTED_NUMBER]"),
    (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "[REDACTED_ID]"),
]


def sanitize(text: str) -> str:
    s = str(text)
    key = get_settings().gnani_api_key
    if key:
        s = s.replace(key, "[REDACTED_KEY]")
    for pat, rep in _PATTERNS:
        s = pat.sub(rep, s)
    return s


class SanitizingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = sanitize(record.getMessage())
        record.args = ()
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not any(isinstance(f, SanitizingFilter) for f in logger.filters):
        logger.addFilter(SanitizingFilter())
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return logger
