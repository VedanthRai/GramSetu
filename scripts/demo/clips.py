"""Voices for the demo video: every voice is AI-generated with Gnani Timbre (live calls through the running server,
so they are counted by the app's usage guard and cached).

  python scripts/demo/clips.py --audition     # synthesise every utterance with each candidate voice, check each with
                                              # live Prisma, pick a voice per language, write demo_assets/voices.json
Source of the sentences: demo_assets/sentences.json. Output: demo_assets/generated/<id>.wav (0.4 s silence added
before and after). Transcripts are never edited: a voice is accepted only on what Prisma actually returned.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
import wave
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo.ff import loudness, run  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SENTENCES = ROOT / "demo_assets" / "sentences.json"
GEN = ROOT / "demo_assets" / "generated"
AUD = GEN / "auditions"
VOICES = ROOT / "demo_assets" / "voices.json"
ASSISTANT_DEFAULT = {"kn-IN": "Saanvi", "hi-IN": "Nalini", "ta-IN": "Asmita", "en-IN": "Kaveri"}
NUM_WORDS = {"2": ["ಎರಡು", "दो", "இரண்டு", "two"]}
ACCEPT_CER = 0.12


def load_sentences() -> dict:
    return json.loads(SENTENCES.read_text(encoding="utf-8"))


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s.lower())
    for digit, words in NUM_WORDS.items():
        for w in words:
            s = s.replace(w, digit)
    s = s.replace("‌", "").replace("‍", "")
    return re.sub(r"[\s\W_]+", "", s)


def cer(ref: str, hyp: str) -> float:
    a, b = _norm(ref), _norm(hyp)
    if not a:
        return 0.0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return round(prev[-1] / len(a), 3)


def _dur(p: Path) -> float:
    with wave.open(str(p)) as w:
        return round(w.getnframes() / w.getframerate(), 2)


def synth(base: str, text: str, lang: str, voice: str, out: Path) -> dict:
    r = httpx.post(base + "/api/speech/synthesize", json={"text": text, "language": lang, "voice": voice,
                                                          "purpose": "demo video asset"}, timeout=90)
    r.raise_for_status()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(r.content)
    return {"cache": r.headers.get("x-cache"), "server_ms": r.headers.get("x-latency-ms"), "model": "timbre-v2.5"}


def prisma(base: str, path: Path, lang: str) -> dict:
    r = httpx.post(base + "/api/speech/transcribe", files={"audio_file": (path.name, path.read_bytes(), "audio/wav")},
                   data={"language": lang}, timeout=90)
    j = r.json()
    return {"status": r.status_code, "transcript": j.get("transcript"), "latency_ms": j.get("latency_ms"), "model": j.get("model")}


def pad(src: Path, dst: Path, seconds: float = 0.4) -> None:
    ms = int(seconds * 1000)
    run(["-i", str(src), "-af", f"adelay={ms}:all=1,apad=pad_dur={seconds}", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(dst)])


def audition(base: str) -> dict:
    cfg = load_sentences()
    result: dict = {"model": "timbre-v2.5", "prisma_model": None, "sentences_sha": hashlib.sha256(SENTENCES.read_bytes()).hexdigest()[:16],
                    "utterances": {}, "narration": {}, "chosen_user_voice": {}, "chosen_narration_voice": None}
    by_lang: dict[str, list] = {}
    for u in cfg["utterances"]:
        by_lang.setdefault(u["language"], []).append(u)
    for lang, utts in by_lang.items():
        scores = {}
        for voice in cfg["user_voice_candidates"][lang]:
            rows = []
            for u in utts:
                raw = AUD / f"{u['id']}__{voice}.wav"
                meta = synth(base, u["native"], lang, voice, raw)
                padded = AUD / f"{u['id']}__{voice}_padded.wav"
                pad(raw, padded)
                p = prisma(base, padded, lang)
                result["prisma_model"] = p.get("model") or result["prisma_model"]
                rows.append({"id": u["id"], "voice": voice, "seconds": _dur(raw), **loudness(raw), **meta,
                             "prisma": p["transcript"], "prisma_ms": p["latency_ms"], "cer": cer(u["native"], p["transcript"] or "")})
                print(f"  {lang} {voice:8s} {u['id']:12s} cer={rows[-1]['cer']:.3f} {rows[-1]['integrated_lufs']} LUFS  {p['transcript']}")
            mean = sum(r["cer"] for r in rows) / len(rows)
            scores[voice] = {"mean_cer": round(mean, 3), "rows": rows, "differs_from_assistant": voice != ASSISTANT_DEFAULT[lang]}
        # Choose: must differ from the assistant voice when possible, then lowest CER, then candidate order (naturalness
        # judged by listening is listed first in sentences.json).
        order = cfg["user_voice_candidates"][lang]
        pick = sorted(scores, key=lambda v: (not scores[v]["differs_from_assistant"], scores[v]["mean_cer"], order.index(v)))[0]
        result["chosen_user_voice"][lang] = pick
        for _v, sc in scores.items():
            for row in sc["rows"]:
                result["utterances"].setdefault(row["id"], {"attempts": []})["attempts"].append(row)
        for u in utts:
            entry = result["utterances"][u["id"]]
            chosen = next(r for r in entry["attempts"] if r["voice"] == pick)
            entry.update({"chosen_voice": pick, "accepted": chosen["cer"] <= ACCEPT_CER, "cer": chosen["cer"], "prisma": chosen["prisma"]})
            pad(AUD / f"{u['id']}__{pick}.wav", GEN / f"{u['id']}.wav")
    # narration voice: audition both on the first line, pick lower loudness deviation from -20 LUFS (clearest level), then order
    nar = cfg["narration"]
    cands = cfg["narration_voice_candidates"]["en-IN"]
    trial = {}
    for v in cands:
        raw = AUD / f"{nar[0]['id']}__{v}.wav"
        synth(base, nar[0]["text"], "en-IN", v, raw)
        p = prisma(base, raw, "en-IN")
        trial[v] = {"seconds": _dur(raw), **loudness(raw), "prisma": p["transcript"], "cer": cer(nar[0]["text"], p["transcript"] or "")}
        print(f"  en-IN {v:8s} narration cer={trial[v]['cer']} {trial[v]['integrated_lufs']} LUFS {trial[v]['seconds']}s")
    nv = sorted(cands, key=lambda v: (trial[v]["cer"], cands.index(v)))[0]
    result["chosen_narration_voice"] = nv
    result["narration_audition"] = trial
    for n in nar:
        raw = AUD / f"{n['id']}__{nv}.wav"
        if not raw.exists():
            synth(base, n["text"], "en-IN", nv, raw)
        pad(raw, GEN / f"{n['id']}.wav", 0.2)
        result["narration"][n["id"]] = {"text": n["text"], "voice": nv, "seconds": _dur(GEN / f"{n['id']}.wav")}
    VOICES.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def resolve_clips(base: str, generate: bool = True) -> dict:
    """Clips for the recorder, from sentences.json + voices.json (auditions run first if needed)."""
    cfg = load_sentences()
    sha = hashlib.sha256(SENTENCES.read_bytes()).hexdigest()[:16]
    v = json.loads(VOICES.read_text(encoding="utf-8")) if VOICES.exists() else None
    if generate and (not v or v.get("sentences_sha") != sha):
        v = audition(base)
    out: dict = {"_by_file": {}}
    for u in cfg["utterances"]:
        path = GEN / f"{u['id']}.wav"
        voice = (v or {}).get("utterances", {}).get(u["id"], {}).get("chosen_voice")
        entry = {"name": u["id"], "lang": u["language"], "text": u["native"], "en": u["english"], "voice": voice,
                 "source": f"AI-generated: Gnani Timbre voice {voice}" if voice else "none (typed)", "synthetic": True,
                 "path": path if path.exists() else None, "file_name": f"{u['id']}.wav",
                 "seconds": _dur(path) if path.exists() else None}
        out[u["id"]] = entry
        if path.exists():
            out["_by_file"][entry["file_name"]] = path
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    base = "http://127.0.0.1:8000"
    if "--audition" in sys.argv:
        r = audition(base)
        print(json.dumps({"user": r["chosen_user_voice"], "narration": r["chosen_narration_voice"],
                          "accepted": {k: v["accepted"] for k, v in r["utterances"].items()}}, ensure_ascii=False))
    else:
        print(json.dumps({k: {kk: str(vv) for kk, vv in e.items()} for k, e in resolve_clips(base, False).items()
                          if not k.startswith("_")}, ensure_ascii=False, indent=1))
