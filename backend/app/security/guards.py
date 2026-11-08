"""Deterministic safety guards that run BEFORE any reasoning provider sees user text.

- Emergency detection (healthcare boundary): stops booking, speaks 112 warning.
- OTP / PIN / password / bank-detail / scam-caller detection: warns, never processes the secret.
- Redaction for external models: phone numbers, long digit runs and ID-like numbers never leave the server.
"""
from __future__ import annotations

import re

_EMERGENCY = [
    r"chest pain", r"heart attack", r"can'?t breathe", r"cannot breathe", r"difficulty breathing", r"not breathing",
    r"severe bleeding", r"bleeding (heavily|a lot)", r"unconscious", r"stroke", r"seizure", r"suicid", r"poison",
    r"seene? (me|mein) dard", r"सीने में दर्द", r"छाती में दर्द", r"सांस (नहीं|लेने में)", r"साँस (नहीं|लेने में)",
    r"बहुत खून", r"खून बह", r"बेहोश", r"दिल का दौरा",
    r"ಎದೆ ನೋವು", r"ಉಸಿರಾಡಲು (ಆಗುತ್ತಿಲ್ಲ|ಕಷ್ಟ)", r"ಉಸಿರು ಕಟ್ಟ", r"ತುಂಬಾ ರಕ್ತ", r"ರಕ್ತಸ್ರಾವ", r"ಪ್ರಜ್ಞೆ ತಪ್ಪ", r"ಹೃದಯಾಘಾತ",
    r"நெஞ்சு வலி", r"மார்பு வலி", r"மூச்சு (விட முடியவில்லை|திணறல்)", r"அதிக இரத்த", r"இரத்தப்போக்கு", r"மயக்க", r"மாரடைப்பு",
]
_SECRET_WORDS = r"(otp|o\.t\.p|one[- ]time (code|password)|pin|password|passcode|cvv|upi pin|atm pin|" \
                r"ओटीपी|ओ टी पी|पिन|पासवर्ड|ಒಟಿಪಿ|ಓಟಿಪಿ|ಪಿನ್|ಪಾಸ್‌ವರ್ಡ್|ஓடிபி|ஓ டி பி|பின்|கடவுச்சொல்)"
_SECRET_SHARE = re.compile(
    _SECRET_WORDS + r".{0,40}(\d[\d\s-]{2,}\d)|"  # "my OTP is 4 8 2 1"
    r"(\d[\d\s-]{2,}\d).{0,20}" + _SECRET_WORDS, re.I)
_SCAM = re.compile(
    r"(someone|caller|person|man|woman|they|he|she).{0,40}(called|asked|wants|asking).{0,40}" + _SECRET_WORDS + r"|"
    + _SECRET_WORDS + r".{0,30}(share|give|tell|send|bata|batao|bataun|dena|dun|de doon|ಹೇಳ|ಕೊಡ|சொல்|கொடு)|"
    r"(share|give|tell|send|बता|ಹೇಳ|ಕೊಡ|சொல்|கொடு).{0,30}" + _SECRET_WORDS + r"|"
    r"(card number|account number|bank details|खाता संख्या|बैंक (डिटेल|विवरण)|ಖಾತೆ ಸಂಖ್ಯೆ|கணக்கு எண்)|"
    r"(फ़ोन|फोन|कॉल).{0,30}(ओटीपी|पिन|पासवर्ड)|(ಫೋನ್|ಕರೆ).{0,30}(ಒಟಿಪಿ|ಓಟಿಪಿ|ಪಿನ್)|(போன்|அழைப்பு).{0,30}(ஓடிபி|பின்)",
    re.I)
_MEDICAL_ADVICE = re.compile(
    r"(which|what) (medicine|tablet|drug)|should i take|dose of|diagnos|what disease|"
    r"कौन सी दवा|क्या दवा|दवाई बताओ|ಯಾವ ಔಷಧಿ|ಯಾವ ಮಾತ್ರೆ|என்ன மருந்து|எந்த மாத்திரை", re.I)

_EMERGENCY_RE = re.compile("|".join(_EMERGENCY), re.I)
_DIGIT_RUN = re.compile(r"(?<!\d)(\+?\d[\d\s-]{6,}\d)(?!\d)")


def is_emergency(text: str) -> bool:
    return bool(_EMERGENCY_RE.search(text))


def is_secret_or_scam(text: str) -> bool:
    return bool(_SECRET_SHARE.search(text) or _SCAM.search(text))


def asks_medical_advice(text: str) -> bool:
    return bool(_MEDICAL_ADVICE.search(text))


def extract_mobile(text: str) -> str | None:
    """Indian mobile numbers are extracted locally; they are never sent to an external model."""
    for m in _DIGIT_RUN.finditer(text):
        digits = re.sub(r"\D", "", m.group(1))
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        if len(digits) == 10 and digits[0] in "6789":
            return digits
    return None


def redact_for_model(text: str) -> str:
    return _DIGIT_RUN.sub("[NUMBER_REDACTED]", text)


INJECTION_MARKERS = re.compile(r"(ignore (all|previous|the above) instructions|system prompt|you are now|"
                               r"disregard .{0,20}instructions|new instructions:|assistant:|<\s*/?\s*system)", re.I)


def looks_like_injection(text: str) -> bool:
    return bool(INJECTION_MARKERS.search(text))
