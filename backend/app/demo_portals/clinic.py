"""Demo clinic portal: real slot table, review page, transactional booking, view and cancel."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.demo_portals.common import PORTAL_SESSIONS, esc, idempotency_key, page
from app.portals.demo_clinic import DEPARTMENT_LABEL, LOCATION_LABEL
from app.services.appointments import service as appt

router = APIRouter(prefix="/portal/clinic", include_in_schema=False)
TITLE = "Community Health Clinic — Demo Booking"
SUB = "Practice clinic for GramSetu demonstrations. Doctors, slots and bookings are synthetic."


def _sess(request: Request) -> tuple[str, dict, bool]:
    sid = request.cookies.get("gs_portal")
    if sid and sid in PORTAL_SESSIONS:
        return sid, PORTAL_SESSIONS[sid], False
    sid = secrets.token_hex(8)
    PORTAL_SESSIONS[sid] = {}
    return sid, PORTAL_SESSIONS[sid], True


def _html(request: Request, body: str, status: int = 200) -> HTMLResponse:
    sid, _, new = _sess(request)
    r = HTMLResponse(page(TITLE, SUB, body), status_code=status)
    if new:
        r.set_cookie("gs_portal", sid, httponly=True, samesite="lax")
    return r


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return _html(request, """<p>Book an outpatient appointment at a demo clinic. This site gives no medical advice.
In an emergency call <b>112</b>.</p><a class="btn" href="/portal/clinic/book">Book a demo appointment</a>""")


@router.get("/book", response_class=HTMLResponse)
def book(request: Request, department: str = "", location: str = "", appointment_date: str = "") -> HTMLResponse:
    dopts = "".join(f'<option value="{k}"{" selected" if k == department else ""}>{v}</option>' for k, v in DEPARTMENT_LABEL.items())
    lopts = "".join(f'<option value="{k}"{" selected" if k == location else ""}>{v}</option>' for k, v in LOCATION_LABEL.items())
    slots_html = ""
    if department in DEPARTMENT_LABEL and location in LOCATION_LABEL and appointment_date:
        slots = appt.free_slots(department, location, appointment_date)
        if slots:
            radios = "".join(
                f'<label><input type="radio" name="slot_id" value="{s["id"]}"> {s["slot_time"]} with {esc(s["doctor"])}</label>'
                for s in slots)
            slots_html = f"""<form method="post" action="/portal/clinic/book/select">
<input type="hidden" name="department" value="{esc(department)}"><input type="hidden" name="location" value="{esc(location)}">
<input type="hidden" name="appointment_date" value="{esc(appointment_date)}">
<fieldset data-testid="slots"><legend>Available slots on {esc(appointment_date)}</legend>{radios}</fieldset>
<label for="patient_name">Patient name (synthetic for demo)</label><input type="text" id="patient_name" name="patient_name" autocomplete="off">
<button type="submit">Continue to review</button></form>"""
        else:
            slots_html = '<div class="err" role="alert" data-error-key="no_slots">No free slots for that day.</div>'
    return _html(request, f"""<h2>Choose department, clinic and day</h2>
<form method="get" action="/portal/clinic/book">
<label for="department">Department</label><select id="department" name="department"><option value="">— choose —</option>{dopts}</select>
<label for="location">Clinic location</label><select id="location" name="location"><option value="">— choose —</option>{lopts}</select>
<label for="appointment_date">Appointment date</label><input type="date" id="appointment_date" name="appointment_date" value="{esc(appointment_date)}">
<button type="submit">Show available slots</button></form>{slots_html}""")


@router.post("/book/select", response_class=HTMLResponse)
def select(request: Request, department: str = Form(""), location: str = Form(""), appointment_date: str = Form(""),
           slot_id: str = Form(""), patient_name: str = Form("")):
    _, s, _ = _sess(request)
    if not slot_id.isdigit() or not patient_name.strip():
        return _html(request, '<div class="err" role="alert">Choose a slot and enter the patient name.</div>'
                     f'<a class="btn" href="/portal/clinic/book?department={esc(department)}&location={esc(location)}&appointment_date={esc(appointment_date)}">Back</a>', 422)
    s["pending"] = {"slot_id": int(slot_id), "patient_name": patient_name.strip()[:80], "department": department,
                    "location": location, "appointment_date": appointment_date}
    return RedirectResponse("/portal/clinic/review", status_code=303)


@router.get("/review", response_class=HTMLResponse)
def review(request: Request) -> HTMLResponse:
    _, s, _ = _sess(request)
    p = s.get("pending")
    if not p:
        return RedirectResponse("/portal/clinic/book", status_code=303)
    slot = next((x for x in appt.free_slots(p["department"], p["location"], p["appointment_date"]) if x["id"] == p["slot_id"]), None)
    if not slot:
        return _html(request, '<div class="err" role="alert" data-error-key="slot_taken">That slot is no longer available.</div>', 409)
    rows = [("Department", DEPARTMENT_LABEL[p["department"]]), ("Clinic", LOCATION_LABEL[p["location"]]),
            ("Date", p["appointment_date"]), ("Time", slot["slot_time"]), ("Doctor", slot["doctor"]), ("Patient", p["patient_name"])]
    table = "".join(f"<tr><td>{k}</td><td>{esc(v)}</td></tr>" for k, v in rows)
    return _html(request, f"""<h2>Review your demo booking</h2><table data-testid="review-table">{table}</table>
<form method="post" action="/portal/clinic/confirm"><button type="submit">Confirm demo booking</button></form>""")


@router.post("/confirm", response_class=HTMLResponse)
def confirm(request: Request):
    _, s, _ = _sess(request)
    p = s.get("pending")
    if not p:
        return RedirectResponse("/portal/clinic/book", status_code=303)
    try:
        ref = appt.book(p["slot_id"], p["patient_name"], idempotency_key(request))
    except appt.SlotUnavailable:
        return _html(request, '<div class="err" role="alert" data-error-key="slot_taken">That slot was just booked by someone else. Please choose another.</div>', 409)
    s.pop("pending", None)
    return RedirectResponse(f"/portal/clinic/booking/{ref}", status_code=303)


@router.get("/booking/{ref}", response_class=HTMLResponse)
def booking(request: Request, ref: str) -> HTMLResponse:
    b = appt.get_booking(ref)
    if not b:
        return _html(request, '<div class="err" role="alert">No such demo booking.</div>', 404)
    cancel = "" if b["status"] == "cancelled" else (
        f'<form method="get" action="/portal/clinic/booking/{esc(ref)}/cancel"><button type="submit">Cancel this demo booking</button></form>')
    return _html(request, f"""<div class="ok"><h2>Demo booking</h2>
<p>Demo reference: <b data-testid="booking-reference">{esc(b['reference'])}</b></p>
<p>Status: <b data-testid="booking-status">{esc(b['status'])}</b></p>
<table><tr><td>Doctor</td><td>{esc(b['doctor'])}</td></tr><tr><td>Date</td><td>{esc(b['slot_date'])}</td></tr>
<tr><td>Time</td><td>{esc(b['slot_time'])}</td></tr><tr><td>Patient</td><td>{esc(b['patient_name'])}</td></tr></table>
<p><b>DEMO RECORD — not a real appointment.</b></p></div>{cancel}""")


@router.get("/booking/{ref}/cancel", response_class=HTMLResponse)
def cancel_page(request: Request, ref: str) -> HTMLResponse:
    if not appt.get_booking(ref):
        return _html(request, '<div class="err" role="alert">No such demo booking.</div>', 404)
    return _html(request, f"""<h2>Cancel demo booking {esc(ref)}?</h2>
<form method="post" action="/portal/clinic/booking/{esc(ref)}/cancel"><button type="submit">Yes, cancel the demo booking</button></form>""")


@router.post("/booking/{ref}/cancel")
def cancel_post(ref: str) -> RedirectResponse:
    appt.cancel(ref)
    return RedirectResponse(f"/portal/clinic/booking/{ref}", status_code=303)
