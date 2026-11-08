"""Sanitized event log + WebSocket fan-out. Timeline entries come only from real events."""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket

from app.core.logging import sanitize
from app.db.database import db, dumps, now_iso

_SUBS: dict[str, set[WebSocket]] = defaultdict(set)


def _safe_json(data: dict) -> str:
    raw = sanitize(dumps(data))
    try:
        json.loads(raw)
    except ValueError:
        return dumps({"note": "detail withheld (could not be sanitised safely)"})
    return raw if len(raw) <= 20000 else dumps({"note": "detail too large to store"})


def _load(raw: str) -> dict:
    try:
        return json.loads(raw or "{}")
    except ValueError:
        return {}


def subscribe(session_id: str, ws: WebSocket) -> None:
    _SUBS[session_id].add(ws)


def unsubscribe(session_id: str, ws: WebSocket) -> None:
    _SUBS[session_id].discard(ws)


async def broadcast(session_id: str, payload: dict) -> None:
    dead = []
    for ws in list(_SUBS.get(session_id, ())):
        try:
            await ws.send_text(json.dumps(payload, ensure_ascii=False, default=str))
        except Exception:
            dead.append(ws)
    for ws in dead:
        unsubscribe(session_id, ws)


async def emit(session_id: str, actor: str, kind: str, description: str, data: dict | None = None,
               persist_data: bool = True) -> dict:
    """persist_data=False: the payload (e.g. a transcript) goes to the live UI only, never to the database."""
    data = data or {}
    desc = sanitize(description)[:300]
    at = now_iso()
    with db() as c:
        cur = c.execute("INSERT INTO events (session_id, at, actor, kind, description, data) VALUES (?,?,?,?,?,?)",
                        (session_id, at, actor, kind, desc, _safe_json(data) if persist_data else "{}"))
        eid = cur.lastrowid
    ev = {"type": "event", "id": eid, "at": at, "actor": actor, "kind": kind, "description": desc, "data": data}
    await broadcast(session_id, ev)
    return ev


def emit_nowait(session_id: str, actor: str, kind: str, description: str, data: dict | None = None,
                persist_data: bool = True) -> None:
    try:
        asyncio.get_running_loop().create_task(emit(session_id, actor, kind, description, data, persist_data))
    except RuntimeError:
        pass


def list_events(session_id: str) -> list[dict]:
    with db() as c:
        rows = c.execute("SELECT id, at, actor, kind, description, data FROM events WHERE session_id=? ORDER BY id",
                         (session_id,)).fetchall()
    return [{**dict(r), "data": _load(r["data"])} for r in rows]
