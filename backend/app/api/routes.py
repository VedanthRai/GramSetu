"""Typed HTTP API. Thin routes; logic lives in services. No unrestricted browser-command endpoint exists."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.core.config import REPO_ROOT, get_settings
from app.core.deps import providers
from app.db.database import db
from app.demo_portals.common import DEMO_SMS
from app.portals.registry import REGISTRY
from app.services import events
from app.services.appointments import service as appt
from app.services.browser.executor import MANAGER, SCREENSHOT_DIR
from app.services.orchestrator import SessionError
from app.services.speech.base import LANGUAGE_NAMES, SpeechError, load_capabilities, verified_languages
from app.services.speech.wav import AudioError, validate_for_stt
from app.services.usage import guard

router = APIRouter(prefix="/api")
SOURCES_FILE = Path(__file__).resolve().parents[1] / "services" / "schemes" / "sources.json"
MAX_UPLOAD = 4 * 1024 * 1024
LangCode = Literal["hi-IN", "kn-IN", "ta-IN", "en-IN"]


def _verified_codes() -> set[str]:
    return {lang["code"] for lang in verified_languages()}


def _err(e: Exception) -> HTTPException:
    if isinstance(e, SessionError):
        return HTTPException(e.status, str(e))
    if isinstance(e, SpeechError):
        return HTTPException(e.status, {"code": e.code, "message": str(e)})
    if isinstance(e, AudioError):
        return HTTPException(400, {"code": e.code, "message": str(e)})
    if isinstance(e, guard.UsageLimitExceeded):
        return HTTPException(429, {"code": "LOCAL_DAILY_LIMIT", "message": str(e)})
    return HTTPException(500, "Unexpected error")


# ---------------------------------------------------------------- status
@router.get("/health")
def health() -> dict:
    p = providers()
    stt, tts, _rsn = p.stt.health.as_dict(), p.tts.health.as_dict(), p.reasoner.health.as_dict()
    degraded = [x["name"] for x in (stt, tts) if not x["configured"] or x["reachable"] is False]
    return {"status": "degraded" if degraded else "ok", "degraded": degraded, "app_mode": get_settings().app_mode,
            "fixture_mode": get_settings().gnani_fixture_mode}


@router.get("/providers/status")
def providers_status() -> dict:
    p = providers()
    r = p.reasoner.health.as_dict()
    r["label"] = p.reasoner.label
    r["is_ai"] = p.reasoner.is_ai
    return {"stt": p.stt.health.as_dict(), "tts": p.tts.health.as_dict(), "reasoning": r,
            "browser": {"name": "Playwright Chromium", "headless": get_settings().browser_headless,
                        "last_error": MANAGER.last_error}}


@router.get("/languages")
def languages() -> dict:
    caps = load_capabilities()
    return {"verified": verified_languages(),
            "pending": [{"code": c, **LANGUAGE_NAMES.get(c, {})} for c, v in caps["languages"].items()
                        if not (v["stt"] == "verified" and v["tts"] == "verified")],
            "code_mixed": caps["code_mixed"], "streaming": caps["streaming"]}


# ---------------------------------------------------------------- speech
@router.post("/speech/transcribe")
async def transcribe(audio_file: UploadFile = File(...), language: str = Form(...),
                     session_id: str | None = Form(None)) -> dict:
    if language not in _verified_codes():
        raise HTTPException(400, {"code": "UNVERIFIED_LANGUAGE", "message": f"{language} is not verified yet."})
    data = await audio_file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, {"code": "TOO_LARGE", "message": "Audio file too large."})
    try:
        info = validate_for_stt(data)
        tr = await providers().stt.transcribe(data, language)
    except (AudioError, SpeechError, guard.UsageLimitExceeded) as e:
        raise _err(e) from e
    if not tr.text:
        raise HTTPException(422, {"code": "NO_SPEECH", "message": "No words were recognised. Please try again."})
    if session_id:
        await events.emit(session_id, "prisma", "transcribed", f"Prisma: voice transcribed ({tr.latency_ms} ms)",
                          {"latency_ms": tr.latency_ms, "audio_seconds": round(info.duration_s, 2), "source": tr.source})
    return {"transcript": tr.text, "literal": tr.literal, "language": language, "latency_ms": tr.latency_ms,
            "model": tr.model, "audio_seconds": round(info.duration_s, 2), "source": tr.source, "request_id": tr.request_id}


class SynthReq(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    language: LangCode
    voice: str | None = Field(default=None, max_length=40)
    session_id: str | None = None
    purpose: str | None = Field(default=None, max_length=40)


_SECRETISH = re.compile(r"(?i)(otp|pin|password|ओटीपी|पासवर्ड|ಒಟಿಪಿ|ஓடிபி)\D{0,15}\d{4,8}")


@router.post("/speech/synthesize")
async def synthesize(req: SynthReq) -> Response:
    if req.language not in _verified_codes():
        raise HTTPException(400, {"code": "UNVERIFIED_LANGUAGE", "message": f"{req.language} is not verified yet."})
    if _SECRETISH.search(req.text):
        raise HTTPException(400, {"code": "SECRET_TEXT", "message": "GramSetu never speaks codes or passwords."})
    try:
        audio = await providers().tts.synthesize(req.text, req.language, req.voice)
    except (SpeechError, guard.UsageLimitExceeded) as e:
        raise _err(e) from e
    if req.session_id:
        await events.emit(req.session_id, "timbre", "spoken",
                          f"Timbre: {req.purpose or 'message'} spoken ({'cache' if audio.cache_hit else f'{audio.latency_ms} ms'})",
                          {"latency_ms": audio.latency_ms, "cache_hit": audio.cache_hit, "voice": audio.voice})
    return Response(audio.wav, media_type="audio/wav",
                    headers={"X-Latency-Ms": str(audio.latency_ms), "X-Cache": "hit" if audio.cache_hit else "miss",
                             "X-Source": audio.source, "X-Voice": audio.voice, "Cache-Control": "no-store"})


# ---------------------------------------------------------------- sessions
class NewSession(BaseModel):
    language: LangCode
    retain_history: bool = False


class ChoiceReq(BaseModel):
    field: str = Field(min_length=1, max_length=40)
    value: str = Field(min_length=1, max_length=80)


class TurnReq(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    raw_transcript: str | None = Field(default=None, max_length=1000)
    choice: ChoiceReq | None = None


class ApproveReq(BaseModel):
    kind: Literal["start", "final"]


class SecretReq(BaseModel):
    value: str = Field(min_length=4, max_length=8)


@router.post("/sessions")
def new_session(req: NewSession) -> dict:
    if req.language not in _verified_codes():
        raise HTTPException(400, "Language not verified")
    o = providers().orchestrator
    return {"session": o.snapshot(o.create_session(req.language, req.retain_history))}


@router.get("/sessions/{sid}")
def get_session(sid: str) -> dict:
    o = providers().orchestrator
    try:
        return {"session": o.snapshot(o.get(sid))}
    except SessionError as e:
        raise _err(e) from e


@router.post("/sessions/{sid}/turns")
async def turn(sid: str, req: TurnReq) -> dict:
    try:
        return await providers().orchestrator.handle_turn(
            sid, req.text, req.raw_transcript, req.choice.model_dump() if req.choice else None)
    except SessionError as e:
        raise _err(e) from e


@router.post("/sessions/{sid}/review")
async def review(sid: str) -> dict:
    try:
        return await providers().orchestrator.review(sid)
    except SessionError as e:
        raise _err(e) from e


@router.post("/sessions/{sid}/approve")
async def approve(sid: str, req: ApproveReq) -> dict:
    try:
        return await providers().orchestrator.approve(sid, req.kind)
    except SessionError as e:
        raise _err(e) from e


@router.post("/sessions/{sid}/cancel")
async def cancel(sid: str) -> dict:
    try:
        return await providers().orchestrator.cancel(sid)
    except SessionError as e:
        raise _err(e) from e


@router.post("/sessions/{sid}/user-input")
async def user_input(sid: str, req: SecretReq) -> dict:
    """Secure relay: the value goes only into the portal's OTP field. It is not logged, stored or sent to a model."""
    try:
        return await providers().orchestrator.user_input(sid, req.value)
    except SessionError as e:
        raise _err(e) from e


@router.post("/sessions/{sid}/resume")
async def resume(sid: str) -> dict:
    try:
        return await providers().orchestrator.resume(sid)
    except SessionError as e:
        raise _err(e) from e


@router.get("/sessions/{sid}/demo-sms")
async def demo_sms(sid: str) -> dict:
    """The user's simulated phone. GramSetu's agent never calls this; only the user's UI shows it."""
    o = providers().orchestrator
    try:
        s = o.get(sid)
    except SessionError as e:
        raise _err(e) from e
    if not s.run or not s.run.ctx:
        return {"message": None}
    cookies = await s.run.ctx.cookies()
    pid = next((c["value"] for c in cookies if c["name"] == "gs_portal"), None)
    msg = DEMO_SMS.get(pid or "")
    return {"message": msg, "notice": "Simulated SMS for the demo portal. In real life this arrives on your phone."}


@router.get("/sessions/{sid}/events")
def session_events(sid: str) -> dict:
    return {"events": events.list_events(sid)}


@router.get("/sessions/{sid}/screenshot")
def screenshot(sid: str, name: str = Query(pattern=r"^\d{3}\.png$")) -> FileResponse:
    if not re.fullmatch(r"[0-9a-f]{32}", sid):
        raise HTTPException(400, "bad id")
    p = SCREENSHOT_DIR / sid / name
    if not p.exists():
        raise HTTPException(404, "not found")
    return FileResponse(p, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.delete("/sessions/{sid}")
def delete_session(sid: str) -> dict:
    providers().orchestrator.delete(sid)
    return {"deleted": True}


@router.websocket("/ws/sessions/{sid}")
async def ws(websocket: WebSocket, sid: str) -> None:
    await websocket.accept()
    events.subscribe(sid, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive pings from client
    except WebSocketDisconnect:
        events.unsubscribe(sid, websocket)


# ---------------------------------------------------------------- reference data
@router.get("/sources")
def sources() -> dict:
    return json.loads(SOURCES_FILE.read_text(encoding="utf-8"))


@router.get("/schemes")
def schemes() -> dict:
    data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    return {"schemes": [{k: s[k] for k in ("scheme_id", "official_name", "official_source_url", "status", "last_verified_at")}
                        for s in data["schemes"]]}


@router.get("/portals")
def portals() -> dict:
    return {"portals": [a.describe() for a in REGISTRY.values()]}


@router.get("/demo/clinic/slots")
def clinic_slots(department: str, location: str, date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
                 period: Literal["morning", "afternoon", "evening", "any"] = "any") -> dict:
    return {"slots": appt.free_slots(department, location, date, period)}


FIXTURE_DIR = REPO_ROOT / "fixtures" / "audio"


@router.get("/fixtures/audio")
def fixtures() -> dict:
    data = json.loads((FIXTURE_DIR / "index.json").read_text(encoding="utf-8"))
    verified = _verified_codes()
    return {"note": data["note"], "fixtures": [f for f in data["fixtures"] if f["language"] in verified
                                                and (FIXTURE_DIR / f["name"]).exists()]}


@router.get("/fixtures/audio/{name}")
def fixture_file(name: str = "") -> FileResponse:
    if not re.fullmatch(r"[A-Za-z0-9_.\-]+\.wav", name):
        raise HTTPException(400, "bad name")
    p = FIXTURE_DIR / name
    if not p.exists():
        raise HTTPException(404, "not found")
    return FileResponse(p, media_type="audio/wav")


@router.get("/usage")
def usage() -> dict:
    return guard.summary()


@router.get("/history")
def history() -> dict:
    with db() as c:
        rows = c.execute("SELECT t.id, t.session_id, t.intent, t.portal_id, t.created_at, t.status, t.data, s.language "
                         "FROM tasks t LEFT JOIN sessions s ON s.id=t.session_id ORDER BY t.created_at DESC LIMIT 100").fetchall()
    return {"tasks": [{**dict(r), "data": json.loads(r["data"] or "{}")} for r in rows]}


@router.get("/eval/results")
def eval_results() -> dict:
    p = REPO_ROOT / "docs" / "eval_results.json"
    if not p.exists():
        return {"status": "pending evaluation"}
    return json.loads(p.read_text(encoding="utf-8"))
