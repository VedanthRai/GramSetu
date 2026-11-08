"""English captions for GramSetu's spoken replies, from the app's OWN bilingual templates (backend/app/services/i18n.py).

Every assistant message is rendered from a template that exists in en-IN, hi-IN, kn-IN and ta-IN. We match the spoken
(native) text back to its template and render the en-IN version with the same values, so the English caption is the
message GramSetu would have said in English. No hand-written or machine-invented translations. Lines that do not match
a template return None and are reported by QC. (The templates themselves are pending native review.)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.services import i18n  # noqa: E402

_PH = re.compile(r"\{(\w+)\}")


def _rev(table: dict[str, dict[str, str]], lang: str) -> dict[str, str]:
    return {v.get(lang, ""): v.get("en-IN", "") for v in table.values() if v.get(lang)}


def _value_en(v: str, lang: str) -> str:
    vals = {**_rev(i18n.M, lang), **_rev(i18n.VALUE_LABELS, lang)}  # e.g. {action} = a whole small template
    if v in vals:
        return vals[v]
    parts = [p.strip() for p in v.split(",")]
    if len(parts) > 1 and all(p in vals for p in parts):
        return ", ".join(vals[p] for p in parts)
    for pn in i18n.PORTAL_NAMES.values():
        if isinstance(pn, dict) and pn.get(lang) == v:
            return pn.get("en-IN", v)
    return v


def _compile(lang: str) -> list[tuple[re.Pattern, str]]:
    out = []
    for _key, tr in i18n.M.items():
        nat, en = tr.get(lang), tr.get("en-IN")
        if not nat or not en:
            continue
        pat = re.escape(nat.strip())
        pat = re.sub(r"\\\{(\w+)\\\}", lambda m: f"(?P<{m.group(1)}>.+?)", pat)
        out.append((re.compile("^" + pat + "$", re.S), en))
    # longer templates first, so specific ones win
    return sorted(out, key=lambda x: -len(x[0].pattern))


def _line(line: str, lang: str, pats) -> str | None:
    line = line.strip()
    if not line:
        return ""
    m = re.match(r"^•\s*(.+?):\s*(.+)$", line)
    if m:
        lab = _rev(i18n.FIELD_LABELS, lang).get(m.group(1).strip())
        if lab:
            return f"• {lab}: {_value_en(m.group(2).strip(), lang)}"
    for pat, en in pats:
        mm = pat.match(line)
        if mm:
            vals = {k: _value_en(v, lang) for k, v in mm.groupdict().items()}
            return _PH.sub(lambda x, vals=vals: vals.get(x.group(1), x.group(0)), en)
    # a line may hold two templates back to back ("A. B?"): try splitting at sentence ends
    parts = re.split(r"(?<=[.?!।])\s+", line)
    for i in range(1, len(parts)):
        a, b = " ".join(parts[:i]), " ".join(parts[i:])
        ea, eb = _line(a, lang, pats), _line(b, lang, pats)
        if ea and eb:
            return ea + " " + eb
    return None


def to_english(text: str, lang: str) -> str | None:
    if lang == "en-IN":
        return text
    pats = _compile(lang)
    out = []
    for ln in text.split("\n"):
        e = _line(ln, lang, pats)
        if e is None:
            return None
        out.append(e)
    return "\n".join(x for x in out if x)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(to_english(sys.argv[1], sys.argv[2]))
