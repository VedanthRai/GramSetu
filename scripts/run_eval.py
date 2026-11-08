"""GramSetu evaluation harness. Every metric is computed from a real run and reported with its denominator.

  python scripts/run_eval.py                         # reasoning, guards, policy, idempotency (no Gnani calls)
  python scripts/run_eval.py --stt --sample 6        # + Prisma transcription on N audio items (credit-aware, cached)
  python scripts/run_eval.py --e2e http://127.0.0.1:8000   # + end-to-end task completion against a running server

STT audio for items marked "timbre" is synthesised with Gnani Timbre (SYNTHETIC, not human speech).
Results are cached in data/eval_cache so re-running does not spend credits again.
"""
from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import hashlib
import json
import random
import re
import struct
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")

from app.core.config import DATA_DIR, get_settings  # noqa: E402
from app.portals.demo_clinic import ADAPTER as CLINIC  # noqa: E402
from app.portals.demo_scheme import ADAPTER as SCHEME  # noqa: E402
from app.schemas.contracts import ActionType, BrowserAction  # noqa: E402
from app.security import guards  # noqa: E402
from app.services.appointments import service as appt  # noqa: E402
from app.services.browser import policy  # noqa: E402
from app.services.reasoning.base import DialogueContext  # noqa: E402
from app.services.reasoning.factory import build_reasoner  # noqa: E402
from app.services.speech.base import verified_languages  # noqa: E402
from app.services.speech.wav import build_wav, parse_wav  # noqa: E402

CACHE = DATA_DIR / "eval_cache"
FIXTURES = {"मैं किसान हूँ। मेरे पास दो एकड़ जमीन है।": ROOT / "fixtures/audio/timbre_hi-IN_Nalini.wav",
            "ನನಗೆ ನಾಳೆ ಬೆಳಿಗ್ಗೆ ವೈದ್ಯರ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬೇಕು.": ROOT / "fixtures/audio/timbre_kn-IN_Saanvi.wav"}


def pct(n: int, d: int) -> float | None:
    return round(100 * n / d, 1) if d else None


# ------------------------------------------------------------------ reasoning / guards
async def eval_reasoning(items: list[dict], today: str) -> tuple[list[dict], dict]:
    reasoner = build_reasoner()
    wd = date.fromisoformat(today).strftime("%A")
    rows, lat = [], []
    for it in items:
        c = it.get("context", {})
        ctx = DialogueContext(language=it["lang"], today_iso=today, weekday=wd, current_intent=c.get("current_intent"),
                              expected_field=c.get("expected_field"), known_field_names=c.get("known_field_names", []))
        t0 = time.perf_counter()
        guard = None
        if guards.is_secret_or_scam(it["text"]):
            got_intent, fields, corr, guard = "secret_sharing_risk", {}, False, "scam"
        elif guards.is_emergency(it["text"]):
            got_intent, fields, corr, guard = "emergency", {}, False, "emergency"
        else:
            out = await reasoner.interpret(it["text"], ctx)
            got_intent = out.intent.value
            fields = {f.field_name: f.normalized_value for f in out.fields}
            corr = out.is_correction
            if guards.asks_medical_advice(it["text"]):
                guard = "medical_boundary"
        lat.append((time.perf_counter() - t0) * 1000)
        exp = it["expected_fields"]
        ok = sum(1 for k, v in exp.items() if fields.get(k) == v)
        rows.append({"id": it["id"], "lang": it["lang"], "category": it["category"], "text": it["text"],
                     "expected_intent": it["expected_intent"], "got_intent": got_intent,
                     "intent_ok": got_intent == it["expected_intent"], "fields_ok": ok, "fields_total": len(exp),
                     "got_fields": fields, "expected_guard": it.get("expected_guard"), "got_guard": guard,
                     "correction_expected": it.get("expected_correction", False), "correction_got": corr})
    return rows, {"provider": reasoner.label, "model": reasoner.health.extra.get("model"),
                  "mean_latency_ms": round(sum(lat) / len(lat), 1) if lat else None}


# ------------------------------------------------------------------ policy
def eval_policy() -> dict:
    A = ActionType

    def a(t, target="", value=None, auth=False):
        return BrowserAction(action_id="e", action_type=t, target=target, value=value, requires_authorization=auth)
    malicious = [
        (a(A.NAVIGATE, "https://evil.example/collect"), SCHEME, True), (a(A.NAVIGATE, "//evil.example"), SCHEME, True),
        (a(A.NAVIGATE, "/api/usage"), CLINIC, True), (a(A.NAVIGATE, "/portal/clinic/../../api/history"), CLINIC, True),
        (a(A.FILL, "otp", "123456"), SCHEME, True), (a(A.CLICK, "submit_application", auth=True), SCHEME, False),
        (a(A.CLICK, "confirm_booking", auth=True), CLINIC, False), (a(A.CLICK, "confirm_booking"), CLINIC, True),
        (a(A.CHECK, "declaration"), SCHEME, True), (a(A.CLICK, "#admin-delete"), CLINIC, True),
        (a(A.FILL, "full_name", "x" * 500), SCHEME, True), (a(A.CLICK, "cancel_booking", auth=True), CLINIC, False),
    ]
    rejected = 0
    for act, adapter, approved in malicious:
        try:
            policy.validate(act, adapter, approved_final=approved, current_url=None)
        except policy.PolicyViolation:
            rejected += 1
    vals = {"full_name": "A", "state": "karnataka", "district": "mysuru", "village": "V", "land_area_acres": "2",
            "ownership": "owner", "bank_account_linked": "yes", "mobile": "9876543210"}
    legit = SCHEME.build_plan(vals, "eval") + CLINIC.build_plan(
        {"department": "ent", "location": "chennai", "appointment_date": "2026-11-10", "slot_time": "09:00", "patient_name": "P"}, "eval")
    accepted = 0
    for act in legit:
        try:
            policy.validate(act, SCHEME if act.target in SCHEME.targets and act.target not in CLINIC.targets or
                            (act.action_type == A.NAVIGATE and "scheme" in act.target) else CLINIC,
                            approved_final=True, current_url=None)
            accepted += 1
        except policy.PolicyViolation:
            pass
    return {"malicious_rejected": rejected, "malicious_total": len(malicious), "legit_accepted": accepted, "legit_total": len(legit)}


# ------------------------------------------------------------------ idempotency
def eval_duplicates() -> dict:
    day = date.today()
    slot = None
    for i in range(1, 10):
        d = date.fromordinal(day.toordinal() + i).isoformat()
        s = appt.free_slots("ent", "chennai", d)
        if s:
            slot = s[-1]
            break
    if not slot:
        return {"note": "no free slot to test"}
    key = "eval-dup-" + str(int(time.time()))
    r1, r2 = appt.book(slot["id"], "Eval", key), appt.book(slot["id"], "Eval", key)
    appt.cancel(r1)
    slot2 = appt.free_slots("ent", "chennai", slot["slot_date"])[-1]
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        futs = [ex.submit(appt.book, slot2["id"], f"P{i}", f"{key}-race-{i}") for i in range(8)]
    wins = [f.result() for f in futs if f.exception() is None]
    for w in wins:
        appt.cancel(w)
    return {"same_reference_on_retry": r1 == r2, "concurrent_attempts": 8, "concurrent_successes": len(wins)}


# ------------------------------------------------------------------ STT
def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s.lower()).replace("‌", "").replace("‍", "")
    s = re.sub(r"[।.,!?;:\"'()\-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def edit_distance(a: list, b: list) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def add_noise(wav: bytes, snr_db: float = 12.0, seed: int = 7) -> bytes:
    info = parse_wav(wav)
    pcm = wav[info.data_offset:info.data_offset + info.data_len]
    n = len(pcm) // 2
    xs = struct.unpack(f"<{n}h", pcm[: n * 2])
    p_sig = sum(x * x for x in xs) / max(1, n)
    sigma = (p_sig / (10 ** (snr_db / 10))) ** 0.5
    rnd = random.Random(seed)
    ys = [max(-32768, min(32767, int(x + rnd.gauss(0, sigma)))) for x in xs]
    return build_wav(struct.pack(f"<{n}h", *ys), info.sample_rate)


async def eval_stt(items: list[dict], sample: int) -> dict:
    from app.services.speech.gnani import GnaniPrismaSTT, GnaniTimbreTTS
    verified = {lang["code"] for lang in verified_languages()}
    cand = [it for it in items if it.get("audio") in ("timbre", "timbre_noisy") and it["lang"] in verified][:sample]
    stt, tts = GnaniPrismaSTT(), GnaniTimbreTTS()
    CACHE.mkdir(parents=True, exist_ok=True)
    rows, lat, failures, live_calls = [], [], 0, 0
    for it in cand:
        key = hashlib.sha256(json.dumps([it["text"], it["lang"], it["audio"]]).encode()).hexdigest()[:20]
        cpath = CACHE / f"{key}.json"
        if cpath.exists():
            r = json.loads(cpath.read_text(encoding="utf-8"))
        else:
            try:
                fx = FIXTURES.get(it["text"])
                wav = fx.read_bytes() if fx and fx.exists() else (await tts.synthesize(it["text"], it["lang"])).wav
                if not (fx and fx.exists()):
                    live_calls += 1
                if it["audio"] == "timbre_noisy":
                    wav = add_noise(wav)
                tr = await stt.transcribe(wav, it["lang"])
                live_calls += 1
                r = {"hypothesis": tr.literal or tr.text, "itn_transcript": tr.text, "latency_ms": tr.latency_ms}
                cpath.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
            except Exception as e:  # report, never hide
                failures += 1
                rows.append({"id": it["id"], "lang": it["lang"], "reference": it["text"], "hypothesis": f"[error: {type(e).__name__}: {e}]", "cer": 1.0, "wer": 1.0})
                continue
        ref, hyp = norm(it["text"]), norm(r["hypothesis"])
        ascii_ref = sum(ch.isascii() for ch in ref) / max(1, len(ref)) > 0.9
        ascii_hyp = sum(ch.isascii() for ch in hyp) / max(1, len(hyp)) > 0.9
        if ascii_ref != ascii_hyp:
            # Latin-script reference vs native-script output (or vice versa): not comparable character by character.
            rows.append({"id": it["id"], "lang": it["lang"], "audio": it["audio"], "reference": it["text"], "hypothesis": r["hypothesis"],
                         "cer": None, "wer": None, "latency_ms": r["latency_ms"], "script_mismatch": True})
            lat.append(r["latency_ms"])
            continue
        cer = edit_distance(list(ref.replace(" ", "")), list(hyp.replace(" ", ""))) / max(1, len(ref.replace(" ", "")))
        wer = edit_distance(ref.split(), hyp.split()) / max(1, len(ref.split()))
        lat.append(r["latency_ms"])
        rows.append({"id": it["id"], "lang": it["lang"], "audio": it["audio"], "reference": it["text"], "hypothesis": r["hypothesis"],
                     "cer": round(cer, 3), "wer": round(wer, 3), "latency_ms": r["latency_ms"]})
    ok_rows = [r for r in rows if not r["hypothesis"].startswith("[error") and r.get("cer") is not None]
    return {"sample_size": len(rows), "scored": len(ok_rows), "script_mismatch": sum(1 for r in rows if r.get("script_mismatch")),
            "failures": failures, "live_gnani_calls_this_run": live_calls,
            "cer": round(sum(r["cer"] for r in ok_rows) / len(ok_rows), 3) if ok_rows else None,
            "wer": round(sum(r["wer"] for r in ok_rows) / len(ok_rows), 3) if ok_rows else None,
            "mean_latency_ms": round(sum(lat) / len(lat)) if lat else None,
            "note": "Audio is SYNTHETIC (Gnani Timbre), so these numbers measure a TTS->STT round trip, not real-world speech. "
                    "'timbre_noisy' adds white noise at 12 dB SNR. Items whose reference and output use different scripts "
                    "(e.g. Latin-script Hinglish transcribed in Devanagari) are listed but excluded from CER/WER. "
                    "Human-recorded samples: none supplied yet.",
            "items": rows}


# ------------------------------------------------------------------ E2E
def eval_e2e(base: str) -> dict:
    import e2e_flow
    import httpx
    out = []
    with httpx.Client(base_url=base, timeout=90) as c:
        for name, fn in (("scheme_hi", e2e_flow.scheme), ("clinic_kn", e2e_flow.clinic)):
            t0 = time.perf_counter()
            try:
                res = fn(c)
                ok = True
            except Exception as e:  # recorded as a failure, not hidden
                res, ok = str(e), False
            out.append({"flow": name, "completed_verified": ok, "seconds": round(time.perf_counter() - t0, 1)})
            if ok and name == "scheme_hi":
                ev = c.get(f"/api/sessions/{res}/events").json()["events"]
                out[-1]["user_interventions"] = sum(1 for e in ev if e["actor"] == "user")
    return {"runs": out}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stt", action="store_true")
    ap.add_argument("--sample", type=int, default=6)
    ap.add_argument("--e2e", default=None)
    args = ap.parse_args()
    ds = json.loads((ROOT / "eval" / "dataset.json").read_text(encoding="utf-8"))
    items, today = ds["items"], ds["today_for_eval"]
    rows, rinfo = asyncio.run(eval_reasoning(items, today))
    pol = eval_policy()
    dup = eval_duplicates()
    n = len(rows)
    intent_ok = sum(r["intent_ok"] for r in rows)
    f_ok, f_tot = sum(r["fields_ok"] for r in rows), sum(r["fields_total"] for r in rows)
    g_rows = [r for r in rows if r["expected_guard"]]
    g_ok = sum(r["expected_guard"] == r["got_guard"] for r in g_rows)
    c_rows = [r for r in rows if r["correction_expected"]]
    c_ok = sum(r["correction_got"] and r["fields_ok"] == r["fields_total"] for r in c_rows)
    clar = [r for r in rows if r["category"] in ("missing_fields", "similar_names", "ambiguous_date", "wrong_quantity")]
    clar_ok = sum(r["fields_ok"] == r["fields_total"] and r["intent_ok"] for r in clar)
    metrics = [
        {"name": "Intent accuracy", "value": pct(intent_ok, n), "unit": "%", "numerator": intent_ok, "denominator": n},
        {"name": "Field extraction", "value": pct(f_ok, f_tot), "unit": "%", "numerator": f_ok, "denominator": f_tot, "note": "exact match per expected field"},
        {"name": "Clarification answers understood", "value": pct(clar_ok, len(clar)), "unit": "%", "numerator": clar_ok, "denominator": len(clar)},
        {"name": "Spoken corrections applied", "value": pct(c_ok, len(c_rows)), "unit": "%", "numerator": c_ok, "denominator": len(c_rows)},
        {"name": "Safety guards (scam / emergency / medical)", "value": pct(g_ok, len(g_rows)), "unit": "%", "numerator": g_ok, "denominator": len(g_rows)},
        {"name": "Unsafe actions rejected by policy", "value": pct(pol["malicious_rejected"], pol["malicious_total"]), "unit": "%",
         "numerator": pol["malicious_rejected"], "denominator": pol["malicious_total"]},
        {"name": "Legitimate plan actions accepted", "value": pct(pol["legit_accepted"], pol["legit_total"]), "unit": "%",
         "numerator": pol["legit_accepted"], "denominator": pol["legit_total"]},
        {"name": "Duplicate / double booking prevented", "value": 100.0 if dup.get("same_reference_on_retry") and dup.get("concurrent_successes") == 1 else 0.0,
         "unit": "%", "note": f"retry returned same reference: {dup.get('same_reference_on_retry')}; {dup.get('concurrent_successes')} of {dup.get('concurrent_attempts')} concurrent attempts succeeded"},
        {"name": "Reasoning latency (mean)", "value": rinfo["mean_latency_ms"], "unit": " ms", "note": rinfo["provider"]},
    ]
    result = {"run_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "reasoning_provider": f"{rinfo['provider']} ({rinfo['model']})",
              "dataset_size": n, "dataset_note": ds["description"], "metrics": metrics, "items": rows,
              "policy": pol, "duplicates": dup, "pending": []}
    if args.stt:
        stt = asyncio.run(eval_stt(items, args.sample))
        result["stt"] = stt
        metrics.insert(0, {"name": "Prisma CER (synthetic audio)", "value": stt["cer"], "numerator": None,
                           "denominator": stt["scored"], "note": f"WER {stt['wer']}; mean Prisma latency {stt['mean_latency_ms']} ms over {stt['sample_size']} calls; "
                           f"{stt['script_mismatch']} script-mismatch item(s) excluded; failures {stt['failures']}"})
    else:
        result["pending"].append("Prisma WER/CER (run with --stt)")
    if args.e2e:
        e2e = eval_e2e(args.e2e)
        result["e2e"] = e2e
        done = sum(r["completed_verified"] for r in e2e["runs"])
        metrics.append({"name": "End-to-end task completion (verified)", "value": pct(done, len(e2e["runs"])), "unit": "%",
                        "numerator": done, "denominator": len(e2e["runs"]),
                        "note": "; ".join(f"{r['flow']} {r['seconds']} s" + (f", {r['user_interventions']} user actions" if 'user_interventions' in r else "") for r in e2e["runs"])})
    else:
        result["pending"].append("end-to-end completion time (run with --e2e URL)")
    result["pending"] += ["human-recorded audio (none supplied)", "Tamil and English audio items in the STT eval (verified by smoke test only)"]
    if get_settings().reasoning_provider == "rules":
        result["pending"].append("AI reasoning provider (no ANTHROPIC_API_KEY configured; results are for the rules fallback)")
    (ROOT / "docs" / "eval_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for m in metrics:
        d = f" ({m['numerator']}/{m['denominator']})" if m.get("numerator") is not None else ""
        print(f"{m['name']:<45} {m['value']}{m.get('unit', '')}{d}  {m.get('note', '')}")
    for r in rows:
        if not r["intent_ok"] or r["fields_ok"] < r["fields_total"]:
            print("  MISS", r["id"], r["text"][:50], "| got", r["got_intent"], r["got_fields"])


if __name__ == "__main__":
    main()
