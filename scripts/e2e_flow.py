"""Drive both workflows end to end against a running server, playing the USER's part with typed turns.

Usage: python scripts/e2e_flow.py [--base http://127.0.0.1:8000] [--only scheme|clinic|cancel]
Makes no Gnani calls (text turns). The OTP is read from the simulated phone endpoint, exactly as a user would.
"""
from __future__ import annotations

import argparse
import sys
import time

import httpx

sys.stdout.reconfigure(encoding="utf-8")


def wait_state(c: httpx.Client, sid: str, states: set[str], timeout: float = 60) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = c.get(f"/api/sessions/{sid}").json()["session"]
        if s["state"] in states:
            return s
        time.sleep(0.4)
    raise TimeoutError(f"state {s['state']} not in {states}")


def say(c: httpx.Client, sid: str, text: str) -> dict:
    r = c.post(f"/api/sessions/{sid}/turns", json={"text": text})
    r.raise_for_status()
    s = r.json()["session"]
    last = [m for m in s["messages"] if m["role"] == "assistant"][-1]
    print(f"  USER: {text}\n  GRAMSETU [{s['state']}]: {last['text'][:160]}")
    return s


def scheme(c: httpx.Client) -> str:
    print("== Workflow A: Hindi scheme application")
    sid = c.post("/api/sessions", json={"language": "hi-IN"}).json()["session"]["id"]
    say(c, sid, "मैं किसान हूँ। मेरे पास दो एकड़ जमीन है। मुझे बताइए कि इस योजना के लिए क्या जानकारी चाहिए और डेमो फॉर्म भरने में मदद कीजिए।")
    say(c, sid, "मेरा नाम रमेश कुमार है")
    s = say(c, sid, "बेंगलुरु")
    assert s["expected_field"] == "district", "ambiguous district must be asked"
    say(c, sid, "बेंगलुरु ग्रामीण")
    say(c, sid, "हरोहल्ली")
    say(c, sid, "अपने नाम पर है")
    say(c, sid, "हाँ, बैंक खाता है")
    s = say(c, sid, "मेरा मोबाइल 9876543210 है")
    assert s["state"] == "PREVIEWING_TASK", s["state"]
    s = say(c, sid, "हाँ")
    assert s["state"] == "AWAITING_CONSENT"
    c.post(f"/api/sessions/{sid}/approve", json={"kind": "start"}).raise_for_status()
    s = wait_state(c, sid, {"AWAITING_USER_ACTION", "FAILED"})
    assert s["state"] == "AWAITING_USER_ACTION", s["messages"][-1]
    sms = c.get(f"/api/sessions/{sid}/demo-sms").json()["message"]
    print("  (user reads code on simulated phone and types it into the secure box)")
    c.post(f"/api/sessions/{sid}/user-input", json={"value": sms["code"]}).raise_for_status()
    s = wait_state(c, sid, {"PAUSED_FOR_CONFIRMATION", "FAILED"})
    assert s["state"] == "PAUSED_FOR_CONFIRMATION", s["messages"][-1]
    c.post(f"/api/sessions/{sid}/approve", json={"kind": "final"}).raise_for_status()
    s = wait_state(c, sid, {"COMPLETED", "FAILED"})
    print("  RESULT:", s["state"], s["result"])
    ev = [e["description"] for e in c.get(f"/api/sessions/{sid}/events").json()["events"] if e["kind"] != "message"]
    assert any("recovered" in d for d in ev), "validation-error recovery should be visible"
    assert any("injection" in d.lower() or "instruction-like" in d for d in ev)
    assert s["state"] == "COMPLETED"
    return sid


def clinic(c: httpx.Client) -> str:
    print("== Workflow B: Kannada clinic booking")
    sid = c.post("/api/sessions", json={"language": "kn-IN"}).json()["session"]["id"]
    say(c, sid, "ನನಗೆ ನಾಳೆ ಬೆಳಿಗ್ಗೆ ವೈದ್ಯರ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬೇಕು. ಕನ್ನಡದಲ್ಲಿ ಸಹಾಯ ಮಾಡಿ.")
    say(c, sid, "ಸಾಮಾನ್ಯ ವೈದ್ಯಕೀಯ")
    s = say(c, sid, "ಬೆಂಗಳೂರು")
    if s["expected_field"] == "appointment_date":  # tomorrow may be a Sunday (clinic closed)
        s = say(c, sid, "ನಾಡಿದ್ದು")
    s = say(c, sid, "ಮೊದಲ")
    s = say(c, sid, "ಸುಮಾ")
    assert s["state"] == "PREVIEWING_TASK", s["state"]
    c.post(f"/api/sessions/{sid}/review").raise_for_status()
    c.post(f"/api/sessions/{sid}/approve", json={"kind": "start"}).raise_for_status()
    s = wait_state(c, sid, {"PAUSED_FOR_CONFIRMATION", "FAILED"})
    assert s["state"] == "PAUSED_FOR_CONFIRMATION", s["messages"][-1]
    s = say(c, sid, "ಹೌದು")
    s = wait_state(c, sid, {"COMPLETED", "FAILED"})
    print("  RESULT:", s["state"], s["result"])
    assert s["state"] == "COMPLETED"
    return s["result"]["reference"]


def cancel(c: httpx.Client, ref: str) -> None:
    print("== Cancellation of", ref)
    sid = c.post("/api/sessions", json={"language": "en-IN" if False else "kn-IN"}).json()["session"]["id"]
    say(c, sid, f"Cancel my booking {ref}")
    c.post(f"/api/sessions/{sid}/review").raise_for_status()
    c.post(f"/api/sessions/{sid}/approve", json={"kind": "start"}).raise_for_status()
    s = wait_state(c, sid, {"PAUSED_FOR_CONFIRMATION", "FAILED"})
    assert s["state"] == "PAUSED_FOR_CONFIRMATION", s["messages"][-1]
    c.post(f"/api/sessions/{sid}/approve", json={"kind": "final"}).raise_for_status()
    s = wait_state(c, sid, {"COMPLETED", "FAILED"})
    print("  RESULT:", s["state"], s["result"])
    assert s["state"] == "COMPLETED"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--only")
    a = ap.parse_args()
    with httpx.Client(base_url=a.base, timeout=60) as c:
        if a.only in (None, "scheme"):
            scheme(c)
        if a.only in (None, "clinic", "cancel"):
            ref = clinic(c)
            if a.only in (None, "cancel"):
                cancel(c, ref)
    print("ALL FLOWS PASSED")
