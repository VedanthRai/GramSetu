"""SQLite storage. Explicit schema initialisation; synthetic demo data only; no secrets stored."""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator
from zoneinfo import ZoneInfo

from app.core.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY, created_at TEXT NOT NULL, language TEXT NOT NULL,
  state TEXT NOT NULL, retain_history INTEGER NOT NULL DEFAULT 0, data TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY, session_id TEXT NOT NULL, intent TEXT, portal_id TEXT,
  created_at TEXT NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS task_states (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, from_state TEXT, to_state TEXT NOT NULL, at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, at TEXT NOT NULL,
  actor TEXT NOT NULL, kind TEXT NOT NULL, description TEXT NOT NULL, data TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, kind TEXT NOT NULL, summary TEXT NOT NULL, at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS browser_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, action_id TEXT NOT NULL, action_type TEXT NOT NULL,
  target TEXT, origin TEXT, route TEXT, status TEXT NOT NULL, detail TEXT, screenshot TEXT, at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY, session_id TEXT NOT NULL, task_id TEXT NOT NULL, evidence_type TEXT NOT NULL,
  source_page TEXT, description TEXT NOT NULL, status TEXT NOT NULL, at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS demo_doctors (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, department TEXT NOT NULL, location TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS demo_slots (
  id INTEGER PRIMARY KEY AUTOINCREMENT, doctor_id TEXT NOT NULL, slot_date TEXT NOT NULL, slot_time TEXT NOT NULL,
  booked INTEGER NOT NULL DEFAULT 0, UNIQUE(doctor_id, slot_date, slot_time)
);
CREATE TABLE IF NOT EXISTS demo_appointments (
  reference TEXT PRIMARY KEY, slot_id INTEGER NOT NULL, patient_name TEXT NOT NULL, status TEXT NOT NULL,
  created_at TEXT NOT NULL, cancelled_at TEXT, idempotency_key TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS demo_applications (
  reference TEXT PRIMARY KEY, data TEXT NOT NULL, created_at TEXT NOT NULL, idempotency_key TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS tts_cache (
  key TEXT PRIMARY KEY, path TEXT NOT NULL, language TEXT, voice TEXT, model TEXT, chars INTEGER, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stt_fixtures (
  audio_sha TEXT PRIMARY KEY, language TEXT NOT NULL, response TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS usage_counters (
  day TEXT NOT NULL, kind TEXT NOT NULL, calls INTEGER NOT NULL DEFAULT 0, audio_seconds REAL NOT NULL DEFAULT 0,
  chars INTEGER NOT NULL DEFAULT 0, cache_hits INTEGER NOT NULL DEFAULT 0, errors INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, kind)
);
"""

DOCTORS = [
    ("doc-gm-blr", "Dr. Asha Rao (demo)", "general_medicine", "bengaluru"),
    ("doc-pe-blr", "Dr. Kiran Shetty (demo)", "pediatrics", "bengaluru"),
    ("doc-or-blr", "Dr. Meera Iyer (demo)", "orthopedics", "bengaluru"),
    ("doc-gm-mys", "Dr. Ravi Gowda (demo)", "general_medicine", "mysuru"),
    ("doc-gm-che", "Dr. Lakshmi Sundaram (demo)", "general_medicine", "chennai"),
    ("doc-en-che", "Dr. Arun Kumar (demo)", "ent", "chennai"),
    ("doc-gm-lko", "Dr. Sunita Verma (demo)", "general_medicine", "lucknow"),
    ("doc-pe-lko", "Dr. Rajesh Mishra (demo)", "pediatrics", "lucknow"),
]
SLOT_TIMES = ["09:00", "09:30", "10:00", "10:30", "11:00", "14:00", "14:30", "16:00", "16:30"]

_lock = threading.Lock()
_initialised: set[str] = set()


def _db_path() -> str:
    return get_settings().db_path


def connect() -> sqlite3.Connection:
    path = _db_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    init_db()
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """BEGIN IMMEDIATE transaction: serialises writers, used for booking to prevent double booking."""
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def today_local() -> date:
    return datetime.now(ZoneInfo(get_settings().timezone)).date()


def init_db(force: bool = False) -> None:
    path = _db_path()
    with _lock:
        if path in _initialised and not force:
            return
        conn = connect()
        try:
            conn.executescript(SCHEMA)
            seed_clinic(conn)
        finally:
            conn.close()
        _initialised.add(path)


def seed_clinic(conn: sqlite3.Connection, days: int = 21) -> None:
    for d in DOCTORS:
        conn.execute("INSERT OR IGNORE INTO demo_doctors VALUES (?,?,?,?)", d)
    start = today_local()
    for i in range(days):
        day = start + timedelta(days=i)
        if day.weekday() == 6:  # demo clinic closed on Sundays
            continue
        for doc_index, d in enumerate(DOCTORS):
            for t_index, t in enumerate(SLOT_TIMES):
                # deterministic pre-booked pattern so availability looks real but is reproducible
                prebooked = 1 if (i + doc_index + t_index) % 4 == 0 else 0
                conn.execute(
                    "INSERT OR IGNORE INTO demo_slots (doctor_id, slot_date, slot_time, booked) VALUES (?,?,?,?)",
                    (d[0], day.isoformat(), t, prebooked),
                )


def now_iso() -> str:
    return datetime.now(ZoneInfo(get_settings().timezone)).isoformat(timespec="seconds")


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)
