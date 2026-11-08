"""Rules fallback (no AI model): deterministic keyword + slot-filling for hi / kn / ta / en.

Limited by design. Labelled "Rules fallback (no AI model)" everywhere it is shown.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from app.schemas.contracts import ExtractedField, Intent, ReasoningOutput, SourceType
from app.services.reasoning.base import DialogueContext
from app.services.speech.base import ProviderHealth


def _any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def _clause(text: str, words: list[str]) -> str:
    """The sentence/clause that mentions one of `words`, so yes/no cues elsewhere in a long utterance don't leak in
    (e.g. "...बैंक खाता भी है, मुझे फॉर्म भरना है" must not read the "ना " of "भरना" as a "no")."""
    for part in re.split(r"[,।.!?;]", text):
        if _any(part, words):
            return part + " "
    return text


SCHEME_WORDS = ["kisan", "किसान", "योजना", "yojana", "scheme", "pm-kisan", "ಕಿಸಾನ್", "ರೈತ", "ಯೋಜನೆ", "விவசாயி",
                "கிசான்", "திட்ட", "farmer", "खेत", "जमीन", "ज़मीन", "ಜಮೀನು", "நிலம்"]
CLINIC_WORDS = ["doctor", "डॉक्टर", "डाक्टर", "appointment", "अपॉइंटमेंट", "अपोइंटमेंट", "ವೈದ್ಯ", "ಡಾಕ್ಟರ್", "ಅಪಾಯಿಂಟ್",
                "மருத்துவர்", "டாக்டர்", "சந்திப்பு", "அப்பாயின்ட்", "clinic", "क्लिनिक", "क्लीनिक", "hospital", "अस्पताल",
                "ಆಸ್ಪತ್ರೆ", "ಕ್ಲಿನಿಕ್", "மருத்துவமனை", "கிளினிக்"]
CANCEL_WORDS = ["cancel", "रद्द", "कैंसल", "ರದ್ದು", "ಕ್ಯಾನ್ಸಲ್", "ரத்து", "கேன்சல்"]
YES = ["yes", "haan", "han ji", "हाँ", "हां", "हा ", "जी हाँ", "ठीक है", "सही है", "ok", "okay", "ಹೌದು", "ಸರಿ",
       "ஆம்", "சரி", "ஆமாம்", "correct", "confirm", "approve", "बिल्कुल"]
NO = ["no", "nahin", "नहीं", "नही", "ना ", "ಇಲ್ಲ", "ಬೇಡ", "இல்லை", "வேண்டாம்", "wrong", "गलत", "ತಪ್ಪು", "தவறு"]
CORRECTION = ["change", "make it", "instead", "बदल", "कर दो", "कर दीजिए", "नहीं,", "ಬದಲಾಯಿಸ", "ಬದಲು", "மாற்று", "பதிலாக",
              "actually", "असल में"]

STATE_WORDS = {
    "karnataka": ["karnataka", "कर्नाटक", "ಕರ್ನಾಟಕ", "கர்நாடக"],
    "uttar_pradesh": ["uttar pradesh", "उत्तर प्रदेश", "यूपी", " up ", "ಉತ್ತರ ಪ್ರದೇಶ", "உத்தரப் பிரதேச", "உத்தர பிரதேச"],
    "tamil_nadu": ["tamil nadu", "तमिलनाडु", "तमिल नाडु", "ತಮಿಳುನಾಡು", "தமிழ்நாடு", "தமிழ் நாடு"],
    "maharashtra": ["maharashtra", "महाराष्ट्र", "ಮಹಾರಾಷ್ಟ್ರ", "மகாராஷ்டிர"],
}
PLACE_WORDS = {
    "bengaluru": ["bengaluru", "bangalore", "बेंगलुरु", "बैंगलोर", "बंगलौर", "ಬೆಂಗಳೂರ", "பெங்களூர"],
    "mysuru": ["mysuru", "mysore", "मैसूर", "ಮೈಸೂರ", "மைசூர"],
    "belagavi": ["belagavi", "belgaum", "बेलगाम", "बेलगावी", "ಬೆಳಗಾವಿ"],
    "lucknow": ["lucknow", "लखनऊ", "ಲಕ್ನೋ", "ಲಖನೌ", "லக்னோ"],
    "varanasi": ["varanasi", "वाराणसी", "बनारस", "ವಾರಾಣಸಿ", "வாரணாசி"],
    "kanpur": ["kanpur", "कानपुर", "ಕಾನ್ಪುರ", "கான்பூர்"],
    "chennai": ["chennai", "चेन्नई", "ಚೆನ್ನೈ", "சென்னை"],
    "coimbatore": ["coimbatore", "कोयंबटूर", "ಕೊಯಮತ್ತೂರು", "கோயம்புத்தூர்", "கோவை"],
    "madurai": ["madurai", "मदुरै", "ಮಧುರೈ", "மதுரை"],
    "pune": ["pune", "पुणे", "ಪುಣೆ", "புனே"],
    "nashik": ["nashik", "नासिक", "ನಾಸಿಕ್", "நாசிக்"],
}
URBAN = ["urban", "शहरी", "शहर", "ನಗರ", "நகர்ப்புற", "நகர"]
RURAL = ["rural", "ग्रामीण", "देहात", "ಗ್ರಾಮಾಂತರ", "ஊரக", "கிராமப்புற"]
NAGAR = ["nagar", "नगर"]
DEHAT = ["dehat", "देहात"]
DEPT_WORDS = {
    "general_medicine": ["general", "सामान्य", "जनरल", "ಸಾಮಾನ್ಯ", "ಜನರಲ್", "பொது", "ஜெனரல்", "family doctor"],
    "pediatrics": ["child", "children", "pediatric", "paediatric", "बच्च", "बाल रोग", "ಮಕ್ಕಳ", "ಮಗು", "குழந்தை"],
    "orthopedics": ["bone", "joint", "ortho", "हड्डी", "जोड़", "ಮೂಳೆ", "எலும்பு", "மூட்டு"],
    "ent": ["ent", "ear", "nose", "throat", "कान", "नाक", "गला", "ಕಿವಿ", "ಮೂಗು", "ಗಂಟಲು", "காது", "மூக்கு", "தொண்டை"],
}
OWNER = ["own name", "my name", "मेरे नाम", "अपने नाम", "खुद के नाम", "मालिक", "owner", "ಸ್ವಂತ", "ನನ್ನ ಹೆಸರಿನಲ್ಲಿ", "ಹೆಸರಲ್ಲೇ", "ಹೆಸರಲ್ಲಿ", "சொந்த", "என் பெயரில்"]
TENANT = ["tenant", "lease", "किराए", "किराये", "बटाई", "ठेके", "ಗೇಣಿ", "ಬಾಡಿಗೆ", "குத்தகை"]
BANK = ["bank", "बैंक", "ಬ್ಯಾಂಕ್", "வங்கி", "खाता", "ಖಾತೆ", "கணக்கு"]
MORNING = ["morning", "मॉर्निंग", "ಮಾರ್ನಿಂಗ್", "மார்னிங்", "सुबह", "सवेरे", "ಬೆಳಿಗ್ಗೆ", "ಬೆಳಗ್ಗೆ", "காலை"]
AFTERNOON = ["afternoon", "आफ्टरनून", "दोपहर", "ಮಧ್ಯಾಹ್ನ", "மதியம்", "பிற்பகல்"]
EVENING = ["evening", "ईवनिंग", "ಈವನಿಂಗ್", "शाम", "ಸಂಜೆ", "மாலை"]

WEEKDAYS = {
    0: ["monday", "सोमवार", "ಸೋಮವಾರ", "திங்கள்"], 1: ["tuesday", "मंगलवार", "ಮಂಗಳವಾರ", "செவ்வாய்"],
    2: ["wednesday", "बुधवार", "ಬುಧವಾರ", "புதன்"], 3: ["thursday", "गुरुवार", "बृहस्पतिवार", "ಗುರುವಾರ", "வியாழன்"],
    4: ["friday", "शुक्रवार", "ಶುಕ್ರವಾರ", "வெள்ளி"], 5: ["saturday", "शनिवार", "ಶನಿವಾರ", "சனி"],
    6: ["sunday", "रविवार", "ಭಾನುವಾರ", "ஞாயிறு"],
}
DAY_AFTER = ["day after tomorrow", "परसों", "ನಾಡಿದ್ದು", "நாளை மறுநாள்"]
TOMORROW = ["tomorrow", "कल", "kal", "ನಾಳೆ", "நாளை"]
TODAY = ["today", "आज", "ಇಂದು", "ಇವತ್ತು", "இன்று"]

NUMBER_WORDS = {
    "डेढ़": 1.5, "ढाई": 2.5, "साढ़े तीन": 3.5, "आधा": 0.5, "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "पांच": 5,
    "छह": 6, "छः": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    "ಒಂದು": 1, "ಎರಡು": 2, "ಮೂರು": 3, "ನಾಲ್ಕು": 4, "ಐದು": 5, "ಆರು": 6, "ಏಳು": 7, "ಎಂಟು": 8, "ಒಂಬತ್ತು": 9, "ಹತ್ತು": 10,
    "ஒன்று": 1, "ஒரு": 1, "இரண்டு": 2, "மூன்று": 3, "நான்கு": 4, "ஐந்து": 5, "ஆறு": 6, "ஏழு": 7, "எட்டு": 8, "பத்து": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "half": 0.5,
}
ACRE = ["acre", "एकड़", "एकर", "ಎಕರೆ", "ஏக்கர்"]
ORDINALS = {0: ["first", "पहला", "पहले", "पहली", "ಮೊದಲ", "முதல்"], 1: ["second", "दूसरा", "दूसरे", "दूसरी", "ಎರಡನೇ", "இரண்டாவது"],
            2: ["third", "तीसरा", "तीसरे", "तीसरी", "ಮೂರನೇ", "மூன்றாவது"]}
NAME_PREFIX = re.compile(r"(my name is|name is|patient(?:'s)? name is|मेरा नाम|मरीज़? का नाम|नाम|ನನ್ನ ಹೆಸರು|ಹೆಸರು|"
                         r"என் பெயர்|பெயர்)\s*[:,-]?\s*", re.I)
NAME_SUFFIX = re.compile(r"\s*(है|हैं|हूँ|हूं|ಆಗಿದೆ|ಇದೆ|ஆகும்|is)\s*[।.!]?\s*$")
REF_RE = re.compile(r"\bGS-?CL-?([A-Z0-9]{4,8})\b", re.I)


def _norm(text: str) -> str:
    return " " + re.sub(r"\s+", " ", text.lower().replace("’", "'")).strip() + " "


def _extract_number(text: str) -> float | None:
    m = re.search(r"(\d+(?:[.,]\d+)?)", text)
    if m:
        return float(m.group(1).replace(",", "."))
    for w in sorted(NUMBER_WORDS, key=len, reverse=True):
        if w in text:
            return float(NUMBER_WORDS[w])
    return None


def _land_area(t: str, expected: bool) -> float | None:
    if _any(t, ACRE) or expected:
        # take the number closest before the acre word
        for a in ACRE:
            i = t.find(a)
            if i >= 0:
                n = _extract_number(t[max(0, i - 25):i])
                if n is not None:
                    return n
        if expected:
            return _extract_number(t)
    return None


def _date(t: str, today: date) -> date | None:
    if _any(t, DAY_AFTER):
        return today + timedelta(days=2)
    for wd, words in WEEKDAYS.items():
        if _any(t, words):
            delta = (wd - today.weekday()) % 7 or 7
            return today + timedelta(days=delta)
    if _any(t, [w for w in TOMORROW if w not in ("kal",)]) or re.search(r"\bkal\b", t):
        return today + timedelta(days=1)
    if _any(t, TODAY):
        return today
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", t)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        y = int(m.group(3)) if m.group(3) else today.year
        y = y + 2000 if y < 100 else y
        try:
            cand = date(y, mo, d)
            return cand if cand >= today else None
        except ValueError:
            return None
    return None


def _slot_time(t: str, offered: list[str]) -> str | None:
    m = re.search(r"\b(\d{1,2})[:.](\d{2})\b", t)
    hh = mm = None
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r"(साढ़े|half past)\s*(\d{1,2}|\w+)", t)
        if m:
            n = _extract_number(m.group(2))
            if n is not None:
                hh, mm = int(n), 30
        else:
            m = re.search(r"\b(\d{1,2})\s*(बजे|baje|o'?clock|ಗಂಟೆ|மணி|am|pm)", t)
            if m:
                hh, mm = int(m.group(1)), 0
    if hh is not None:
        if (_any(t, AFTERNOON + EVENING) or "pm" in t) and hh < 8:
            hh += 12
        if hh < 8 and not _any(t, MORNING):
            hh += 12
        cand = f"{hh:02d}:{mm:02d}"
        return cand if (not offered or cand in offered) else cand
    for idx, words in ORDINALS.items():
        if _any(t, words) and idx < len(offered):
            return offered[idx]
    return None


def _strip_name(text: str) -> str:
    s = NAME_PREFIX.sub("", text.strip(), count=1)
    s = NAME_SUFFIX.sub("", s)
    s = re.sub(r"[।.!?,\"]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()[:80]


def _inline_name(fragment: str) -> str:
    """A name mentioned inside a longer sentence. Speech transcripts often have no punctuation ("my name is Ramesh Kumar
    from Bengaluru village Harohalli ..."), so keep at most 3 words and stop at the first word we recognise as
    something else (a place, a village/land/bank/scheme keyword, a number)."""
    stop: list[str] = SCHEME_WORDS + CLINIC_WORDS + BANK + ACRE + OWNER + TENANT + URBAN + RURAL + TOMORROW + TODAY
    for words in list(PLACE_WORDS.values()) + list(STATE_WORDS.values()):
        stop += list(words)
    stop += ["village", "from", "गाँव", "गांव", "ग्राम", "से", "ಊರು", "ಗ್ರಾಮ", "ಕಡೆ", "ನಾನು", "ಮತ್ತು", "और", "मैं",
             "கிராமம்", "ஊர்", "நான்", "and", "i", "am", "is", "farmer", "किसान", "ರೈತ", "விவசாயி"]
    whole = {"है", "हैं", "हूँ", "हूं", "ಆಗಿದೆ", "ಇದೆ", "ஆகும்", "is", "am", "i", "and"}
    out = []
    for w in _strip_name(fragment).split():
        lw = w.lower()
        if lw in whole or any(x.lower() in lw for x in stop if len(x) > 2) or any(ch.isdigit() for ch in w):
            break
        out.append(w)
        if len(out) == 3:
            break
    return " ".join(out)


class RulesReasoner:
    label = "Rules fallback (no AI model)"
    is_ai = False

    def __init__(self) -> None:
        self.health = ProviderHealth(name=self.label, kind="reasoning", configured=True, reachable=True,
                                     extra={"model": "none", "provider": "rules"})

    async def interpret(self, text: str, ctx: DialogueContext) -> ReasoningOutput:
        return self.interpret_sync(text, ctx)

    def interpret_sync(self, text: str, ctx: DialogueContext) -> ReasoningOutput:
        t = _norm(text)
        today = date.fromisoformat(ctx.today_iso)
        fields: list[ExtractedField] = []
        expected = ctx.expected_field

        def add(name: str, value: str, expr: str = "") -> None:
            if not any(f.field_name == name for f in fields):
                fields.append(ExtractedField(field_name=name, normalized_value=value,
                                             original_user_expression=(expr or text)[:300],
                                             source_type=SourceType.USER_SPOKEN))

        is_cancel = _any(t, CANCEL_WORDS)
        has_clinic = _any(t, CLINIC_WORDS)
        has_scheme = _any(t, SCHEME_WORDS)
        is_correction = _any(t, CORRECTION) and bool(ctx.known_field_names)

        # ---- intent
        if is_cancel and (has_clinic or REF_RE.search(text) or ctx.current_intent == "cancel_appointment"
                          or "booking" in t or "बुकिंग" in t or "ಬುಕಿಂಗ್" in t or "முன்பதிவு" in t):
            intent = Intent.CANCEL_APPOINTMENT
        elif has_clinic and ctx.current_intent != "clinic_appointment":
            intent = Intent.CLINIC_APPOINTMENT
        elif has_scheme and ctx.current_intent != "scheme_application" and not ctx.current_intent:
            intent = Intent.SCHEME_APPLICATION
        elif ctx.current_intent:
            intent = Intent.PROVIDE_INFO
        else:
            intent = Intent.UNSUPPORTED
        short = len(t.split()) <= 4
        if ctx.current_intent and short and not is_correction and expected not in ("bank_account_linked",):
            if _any(t, YES) and not _any(t, NO):
                intent = Intent.CONFIRM
            elif _any(t, NO) and not any(_any(t, w) for w in WEEKDAYS.values()):
                intent = Intent.DENY

        scheme_ctx = intent == Intent.SCHEME_APPLICATION or ctx.current_intent == "scheme_application"
        clinic_ctx = intent == Intent.CLINIC_APPOINTMENT or ctx.current_intent == "clinic_appointment"

        # ---- scheme fields
        if scheme_ctx:
            area = _land_area(t, expected == "land_area_acres")
            if area is not None and 0 < area <= 1000:
                add("land_area_acres", f"{area:g}")
            for st, words in STATE_WORDS.items():
                if _any(t, words):
                    add("state", st)
            for place, words in PLACE_WORDS.items():
                if _any(t, words):
                    if place == "bengaluru":
                        if _any(t, URBAN):
                            add("district", "bengaluru_urban")
                        elif _any(t, RURAL):
                            add("district", "bengaluru_rural")
                        else:
                            add("district_ambiguous", "bengaluru")
                    elif place == "kanpur":
                        if _any(t, DEHAT):
                            add("district", "kanpur_dehat")
                        elif _any(t, NAGAR) or _any(t, URBAN):
                            add("district", "kanpur_nagar")
                        else:
                            add("district_ambiguous", "kanpur")
                    else:
                        add("district", place)
            if expected == "district" and ctx.offered_options.get("district"):
                for idx, words in ORDINALS.items():
                    if _any(t, words) and idx < len(ctx.offered_options["district"]):
                        add("district", ctx.offered_options["district"][idx])
                if _any(t, URBAN):
                    add("district", next((d for d in ctx.offered_options["district"] if d.endswith("urban") or d.endswith("nagar")), ""))
                if _any(t, RURAL):
                    add("district", next((d for d in ctx.offered_options["district"] if d.endswith("rural") or d.endswith("dehat")), ""))
            if _any(t, TENANT):
                add("ownership", "tenant")
            elif _any(t, OWNER) or (expected == "ownership" and _any(t, YES)):
                add("ownership", "owner")
            if expected == "bank_account_linked" or _any(t, BANK):
                bt = _clause(t, BANK) if _any(t, BANK) else t
                if _any(bt, NO) or "no bank" in bt or "नहीं है" in bt:
                    add("bank_account_linked", "no")
                elif _any(bt, YES) or "है" in bt or "ಇದೆ" in bt or "உள்ளது" in bt or "இருக்கு" in bt or "have" in bt:
                    add("bank_account_linked", "yes")
            m = re.search(r"(?:^|\s)(?:village|गाँव|गांव|ग्राम|ಗ್ರಾಮ|ಊರು|கிராமம்|ஊர்)(?:\s+(?:is|का नाम|ಹೆಸರು|பெயர்))?\s*[:-]?\s+([^\s,।.]+)", text, re.I)
            if m and m.group(1).lower() not in ("is", "का", "की", "है"):
                add("village", m.group(1))
            elif expected == "village" and len(text.split()) <= 5:
                add("village", _strip_name(text))
            if expected == "full_name" or NAME_PREFIX.search(text):
                if expected == "full_name" or re.search(r"(my name is|मेरा नाम|ನನ್ನ ಹೆಸರು|என் பெயர்)", text, re.I):
                    name = _strip_name(text) if expected == "full_name" else _inline_name(
                        re.split(r"[।.,]", text[NAME_PREFIX.search(text).start():])[0])
                    if name:
                        add("full_name", name)

        # ---- clinic fields
        if clinic_ctx:
            for dept, words in DEPT_WORDS.items():
                if _any(t, [f" {w}" if w == "ent" else w for w in words]):
                    add("department", dept)
                    break
            for place in ("bengaluru", "mysuru", "chennai", "lucknow"):
                if _any(t, PLACE_WORDS[place]):
                    add("location", place)
            d = _date(t, today)
            if d:
                add("appointment_date", d.isoformat())
            if _any(t, MORNING):
                add("time_preference", "morning")
            elif _any(t, AFTERNOON):
                add("time_preference", "afternoon")
            elif _any(t, EVENING):
                add("time_preference", "evening")
            st = _slot_time(t, ctx.offered_options.get("slot_time", []))
            if st:
                add("slot_time", st)
            if expected == "patient_name" or re.search(r"(patient|मरीज़|मरीज|ರೋಗಿ|நோயாளி|my name is|मेरा नाम|ನನ್ನ ಹೆಸರು|என் பெயர்)", text, re.I):
                if expected == "patient_name":
                    name = _strip_name(text)
                else:
                    mm = NAME_PREFIX.search(text)
                    name = _inline_name(re.split(r"[।.,]", text[mm.start():])[0]) if mm else ""
                if name and not _any(_norm(name), CLINIC_WORDS):
                    add("patient_name", name)

        if intent == Intent.CANCEL_APPOINTMENT or ctx.current_intent == "cancel_appointment":
            m = REF_RE.search(re.sub(r"[\s-]+", "-", text.upper()))
            if m:
                add("booking_reference", f"GS-CL-{m.group(1).upper()}")

        if intent == Intent.PROVIDE_INFO and not fields and not is_correction:
            intent = Intent.UNSUPPORTED if not ctx.current_intent else Intent.PROVIDE_INFO
        return ReasoningOutput(intent=intent, fields=fields, is_correction=is_correction and bool(fields),
                               detected_language=ctx.language, notes="rules")
