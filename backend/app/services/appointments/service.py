"""Demo clinic data: real SQLite slots, transactional booking, idempotent, no double booking."""
from __future__ import annotations

import secrets

from app.db.database import db, now_iso, transaction

PERIODS = {"morning": ("00:00", "12:00"), "afternoon": ("12:00", "16:00"), "evening": ("16:00", "23:59"),
           "any": ("00:00", "23:59")}


class SlotUnavailable(RuntimeError):
    pass


def free_slots(department: str, location: str, slot_date: str, period: str = "any") -> list[dict]:
    lo, hi = PERIODS.get(period, PERIODS["any"])
    with db() as c:
        rows = c.execute(
            "SELECT s.id, s.slot_time, s.slot_date, d.name AS doctor, d.id AS doctor_id FROM demo_slots s "
            "JOIN demo_doctors d ON d.id=s.doctor_id WHERE d.department=? AND d.location=? AND s.slot_date=? "
            "AND s.booked=0 AND s.slot_time>=? AND s.slot_time<? ORDER BY s.slot_time",
            (department, location, slot_date, lo, hi)).fetchall()
    return [dict(r) for r in rows]


def find_slot(department: str, location: str, slot_date: str, slot_time: str) -> dict | None:
    with db() as c:
        r = c.execute(
            "SELECT s.id, s.slot_time, s.slot_date, s.booked, d.name AS doctor FROM demo_slots s JOIN demo_doctors d "
            "ON d.id=s.doctor_id WHERE d.department=? AND d.location=? AND s.slot_date=? AND s.slot_time=?",
            (department, location, slot_date, slot_time)).fetchone()
    return dict(r) if r else None


def book(slot_id: int, patient_name: str, idempotency_key: str) -> str:
    with transaction() as c:
        existing = c.execute("SELECT reference FROM demo_appointments WHERE idempotency_key=?",
                             (idempotency_key,)).fetchone()
        if existing:
            return existing["reference"]  # duplicate submission: return the original booking, never book twice
        cur = c.execute("UPDATE demo_slots SET booked=1 WHERE id=? AND booked=0", (slot_id,))
        if cur.rowcount != 1:
            raise SlotUnavailable("This slot was just booked by someone else.")
        ref = "GS-CL-" + secrets.token_hex(3).upper()
        c.execute("INSERT INTO demo_appointments (reference, slot_id, patient_name, status, created_at, idempotency_key)"
                  " VALUES (?,?,?,?,?,?)", (ref, slot_id, patient_name[:80], "booked", now_iso(), idempotency_key))
        return ref


def get_booking(reference: str) -> dict | None:
    with db() as c:
        r = c.execute(
            "SELECT a.reference, a.status, a.patient_name, a.created_at, a.cancelled_at, a.idempotency_key, s.slot_date, "
            "s.slot_time, d.name AS doctor, d.department, d.location FROM demo_appointments a JOIN demo_slots s "
            "ON s.id=a.slot_id JOIN demo_doctors d ON d.id=s.doctor_id WHERE a.reference=?", (reference,)).fetchone()
    return dict(r) if r else None


def find_by_idempotency(key: str) -> dict | None:
    with db() as c:
        r = c.execute("SELECT reference FROM demo_appointments WHERE idempotency_key=?", (key,)).fetchone()
    return get_booking(r["reference"]) if r else None


def cancel(reference: str) -> bool:
    with transaction() as c:
        r = c.execute("SELECT slot_id, status FROM demo_appointments WHERE reference=?", (reference,)).fetchone()
        if not r:
            return False
        if r["status"] == "cancelled":
            return True
        c.execute("UPDATE demo_appointments SET status='cancelled', cancelled_at=? WHERE reference=?",
                  (now_iso(), reference))
        c.execute("UPDATE demo_slots SET booked=0 WHERE id=?", (r["slot_id"],))
        return True
