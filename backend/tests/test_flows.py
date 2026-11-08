"""Integration tests through the real HTTP API, real Playwright browser and real demo portals (no Gnani calls)."""
from __future__ import annotations

import concurrent.futures
import time

import e2e_flow
import pytest
from app.db.database import db, today_local
from app.services.appointments import service as appt
from playwright.async_api import Error as PlaywrightError


def wait(c, sid, states, timeout=60):
    return e2e_flow.wait_state(c, sid, states, timeout)


def events(c, sid):
    return [e["description"] for e in c.get(f"/api/sessions/{sid}/events").json()["events"]]


def test_health_reports_each_provider_honestly(client):
    st = client.get("/api/providers/status").json()
    assert st["reasoning"]["label"] == "Rules fallback (no AI model)" and st["reasoning"]["is_ai"] is False
    assert st["stt"]["configured"] is False  # tests run without a key: must not look operational
    assert client.get("/api/health").json()["status"] == "degraded"


def test_workflow_a_scheme_end_to_end(client):
    sid = e2e_flow.scheme(client)
    ev = events(client, sid)
    assert any("instruction-like text" in d for d in ev), "prompt injection must be detected and ignored"
    assert any("validation error, recovered" in d for d in ev)
    assert not any("evil.example" in d for d in ev)
    with db() as c:
        audit = [dict(r) for r in c.execute("SELECT origin, route FROM browser_audit WHERE session_id=?", (sid,))]
    assert audit and all(a["origin"] == "http://127.0.0.1:8765" and a["route"].startswith("/portal/scheme") for a in audit)


def test_workflow_b_clinic_and_cancel(client):
    ref = e2e_flow.clinic(client)
    assert appt.get_booking(ref)["status"] == "booked"
    e2e_flow.cancel(client, ref)
    assert appt.get_booking(ref)["status"] == "cancelled"


def test_otp_never_stored_or_logged(client):
    sid = client.post("/api/sessions", json={"language": "hi-IN"}).json()["session"]["id"]
    r = client.post(f"/api/sessions/{sid}/turns", json={"text": "मेरा ओटीपी 482193 है"}).json()["session"]
    assert all("482193" not in m["text"] for m in r["messages"])
    assert r["messages"][-1]["kind"] == "warning"
    with db() as c:
        dump = " ".join(str(tuple(row)) for t in ("events", "sessions", "tasks") for row in c.execute(f"SELECT * FROM {t}"))
    assert "482193" not in dump


def test_emergency_stops_booking(client):
    sid = client.post("/api/sessions", json={"language": "en-IN" if False else "hi-IN"}).json()["session"]["id"]
    client.post(f"/api/sessions/{sid}/turns", json={"text": "कल सुबह डॉक्टर की अपॉइंटमेंट चाहिए"})
    s = client.post(f"/api/sessions/{sid}/turns", json={"text": "मुझे सीने में दर्द है"}).json()["session"]
    assert s["task"] is None and s["messages"][-1]["kind"] == "emergency" and "112" in s["messages"][-1]["text"]


def test_approval_required_before_execution(client):
    sid = client.post("/api/sessions", json={"language": "hi-IN"}).json()["session"]["id"]
    client.post(f"/api/sessions/{sid}/turns", json={"text": "कल सुबह डॉक्टर की अपॉइंटमेंट चाहिए"})
    assert client.post(f"/api/sessions/{sid}/approve", json={"kind": "start"}).status_code == 409
    assert client.post(f"/api/sessions/{sid}/approve", json={"kind": "final"}).status_code == 409
    assert client.post(f"/api/sessions/{sid}/approve", json={"kind": "delete_everything"}).status_code == 422


def test_session_isolation(client):
    a = client.post("/api/sessions", json={"language": "hi-IN"}).json()["session"]["id"]
    b = client.post("/api/sessions", json={"language": "kn-IN"}).json()["session"]["id"]
    client.post(f"/api/sessions/{a}/turns", json={"text": "मेरा नाम सीता देवी है, मैं किसान हूँ"})
    sb = client.get(f"/api/sessions/{b}").json()["session"]
    assert sb["task"] is None and all("सीता" not in m["text"] for m in sb["messages"])
    assert client.get("/api/sessions/does-not-exist").status_code == 404


def test_cancel_mid_execution_reports_progress(client):
    sid = client.post("/api/sessions", json={"language": "hi-IN"}).json()["session"]["id"]
    for t in ["मैं किसान हूँ, मेरे पास 3 एकड़ जमीन है", "मेरा नाम गीता है", "मैसूर", "हुनसूर", "अपने नाम पर", "हाँ बैंक खाता है", "9876501234"]:
        client.post(f"/api/sessions/{sid}/turns", json={"text": t})
    client.post(f"/api/sessions/{sid}/review")
    client.post(f"/api/sessions/{sid}/approve", json={"kind": "start"})
    wait(client, sid, {"AWAITING_USER_ACTION"})
    s = client.post(f"/api/sessions/{sid}/cancel").json()["session"]
    assert s["state"] == "CANCELLED"
    assert "Nothing was submitted" in s["messages"][-1]["text"]
    with db() as c:
        assert c.execute("SELECT COUNT(*) FROM demo_applications WHERE idempotency_key=?",
                         (s["task"]["task_id"],)).fetchone()[0] == 0


def _a_free_slot():
    day = today_local()
    for i in range(1, 8):
        d = (day.fromordinal(day.toordinal() + i)).isoformat()
        slots = appt.free_slots("general_medicine", "chennai", d)
        if slots:
            return slots[0]
    pytest.skip("no free slot")


def test_duplicate_submission_returns_same_booking():
    s = _a_free_slot()
    r1 = appt.book(s["id"], "Test Patient", "idem-dup-1")
    r2 = appt.book(s["id"], "Test Patient", "idem-dup-1")
    assert r1 == r2
    with db() as c:
        assert c.execute("SELECT COUNT(*) FROM demo_appointments WHERE idempotency_key='idem-dup-1'").fetchone()[0] == 1


def test_no_double_booking_under_concurrency():
    s = _a_free_slot()
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        futs = [ex.submit(appt.book, s["id"], f"P{i}", f"race-{i}") for i in range(8)]
    ok = [f for f in futs if f.exception() is None]
    assert len(ok) == 1
    assert all(isinstance(f.exception(), appt.SlotUnavailable) for f in futs if f.exception())


def test_verifier_never_claims_success_without_record():
    from app.services.browser.verifier import verify
    assert verify("demo_scheme", "no-such-task", None, {})["verified"] is False
    assert verify("demo_clinic", "no-such-task", "GS-CL-FAKE", {})["verified"] is False


def test_tts_refuses_secret_text_and_unverified_language(client):
    r = client.post("/api/speech/synthesize", json={"text": "आपका OTP 482193 है", "language": "hi-IN"})
    assert r.status_code == 400 and "SECRET_TEXT" in r.text
    r = client.post("/api/speech/synthesize", json={"text": "hello", "language": "ml-IN"})
    assert r.status_code == 422  # not one of the supported language codes


def test_speech_without_key_fails_clearly(client):
    r = client.post("/api/speech/synthesize", json={"text": "नमस्ते टेस्ट " + str(time.time()), "language": "hi-IN"})
    assert r.status_code == 503 and "NOT_CONFIGURED" in r.text


def test_usage_guard_blocks_over_limit(monkeypatch):
    from app.core.config import get_settings
    from app.services.usage import guard
    monkeypatch.setattr(get_settings(), "daily_gnani_request_limit", 1)
    guard.record("tts", calls=1)
    with pytest.raises(guard.UsageLimitExceeded):
        guard.check_allowed()


def test_external_navigation_blocked_at_network_layer(server):
    import asyncio

    from app.services.browser.executor import BrowserManager

    async def go():
        # A fresh manager: the app's singleton browser belongs to the server thread's event loop.
        manager = BrowserManager()
        ctx = await manager.new_context("net-test")
        page = await ctx.new_page()
        with pytest.raises(PlaywrightError):
            await page.goto("https://example.com/", timeout=5000)
        with pytest.raises(PlaywrightError):
            await page.goto(server + "/api/usage", timeout=5000)
        page = await ctx.new_page()  # the old page is showing the blocked-request error page
        await page.goto(server + "/portal/clinic/", timeout=5000)
        assert "Demo Booking" in await page.title()
        await ctx.close()
        await manager.close()

    asyncio.run(go())
