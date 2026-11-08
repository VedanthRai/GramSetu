"""State verifier: completion only with evidence from the portal's own persisted records."""
from __future__ import annotations

from app.db.database import db
from app.services.appointments import service as appt


def verify(portal_id: str, task_id: str, page_reference: str | None, values: dict[str, str],
           check_only: bool = False) -> dict:
    if portal_id == "demo_scheme":
        with db() as c:
            row = c.execute("SELECT reference, created_at FROM demo_applications WHERE idempotency_key=?",
                            (task_id,)).fetchone()
        if not row:
            return {"verified": False, "description": "no stored demo application found for this task"}
        if page_reference is not None and page_reference != row["reference"]:
            return {"verified": False, "description": "page reference does not match the stored record"}
        return {"verified": True, "reference": row["reference"], "record": dict(row),
                "description": f"record found — demo application {row['reference']} stored"}
    if portal_id == "demo_clinic":
        b = appt.find_by_idempotency(task_id)
        if not b or b["status"] != "booked":
            return {"verified": False, "description": "no booked demo appointment found for this task"}
        if page_reference is not None and page_reference != b["reference"]:
            return {"verified": False, "description": "page reference does not match the stored booking"}
        if not check_only and (b["slot_date"] != values.get("appointment_date") or b["slot_time"] != values.get("slot_time")):
            return {"verified": False, "description": "stored booking date/time differs from what you approved"}
        return {"verified": True, "reference": b["reference"], "record": b,
                "description": f"record found — booking {b['reference']} with {b['doctor']} on {b['slot_date']} {b['slot_time']}"}
    if portal_id == "demo_clinic_cancel":
        ref = values.get("booking_reference", "")
        b = appt.get_booking(ref)
        if not b:
            return {"verified": False, "description": "booking reference not found"}
        if b["status"] != "cancelled":
            return {"verified": False, "description": "booking is still active"}
        return {"verified": True, "reference": ref, "record": b, "description": f"record shows booking {ref} cancelled"}
    return {"verified": False, "description": "no verifier for this portal"}
