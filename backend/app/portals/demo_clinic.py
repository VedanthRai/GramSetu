"""Adapter for the locally hosted demo clinic portal."""
from __future__ import annotations

from app.portals.base import FieldSpec, Locator, PortalAdapter, act
from app.schemas.contracts import ActionType as A
from app.schemas.contracts import BrowserAction, Sensitivity

DEPARTMENTS = ("general_medicine", "pediatrics", "orthopedics", "ent")
LOCATIONS = ("bengaluru", "mysuru", "chennai", "lucknow")
DEPARTMENT_LABEL = {"general_medicine": "General Medicine", "pediatrics": "Pediatrics", "orthopedics": "Orthopedics", "ent": "ENT"}
LOCATION_LABEL = {"bengaluru": "Bengaluru", "mysuru": "Mysuru", "chennai": "Chennai", "lucknow": "Lucknow"}

FIELDS = {
    "department": FieldSpec("department", "select", options=DEPARTMENTS, ask_key="ask.department"),
    "location": FieldSpec("location", "select", options=LOCATIONS, ask_key="ask.location"),
    "appointment_date": FieldSpec("appointment_date", "date", ask_key="ask.appointment_date"),
    "time_preference": FieldSpec("time_preference", "select", required=False,
                                 options=("morning", "afternoon", "evening", "any")),
    "slot_time": FieldSpec("slot_time", "select", ask_key="ask.slot_time"),
    "doctor": FieldSpec("doctor", "derived", required=False),
    "patient_name": FieldSpec("patient_name", "text", sensitivity=Sensitivity.PERSONAL, ask_key="ask.patient_name"),
}
CANCEL_FIELDS = {"booking_reference": FieldSpec("booking_reference", "text", ask_key="ask.booking_reference")}

TARGETS = {
    "book_link": Locator("role_link", "Book a demo appointment"),
    "department": Locator("label", "Department"),
    "location": Locator("label", "Clinic location"),
    "appointment_date": Locator("label", "Appointment date"),
    "show_slots": Locator("role_button", "Show available slots"),
    "slot": Locator("role_radio", ""),  # accessible name built from slot time, resolved at run time
    "patient_name": Locator("label", "Patient name (synthetic for demo)"),
    "continue_review": Locator("role_button", "Continue to review"),
    "confirm_booking": Locator("role_button", "Confirm demo booking"),
    "reference": Locator("test_id", "booking-reference"),
    "cancel_booking": Locator("role_button", "Cancel this demo booking"),
    "confirm_cancel": Locator("role_button", "Yes, cancel the demo booking"),
    "booking_status": Locator("test_id", "booking-status"),
}


def _book_plan(adapter: PortalAdapter, v: dict[str, str], task_id: str) -> list[BrowserAction]:
    p = adapter.route_prefix
    return [
        act(A.NAVIGATE, f"{p}/", expected=f"route:{p}/", why="Open the demo clinic portal."),
        act(A.CLICK, "book_link", expected=f"route:{p}/book", why="Go to the booking form."),
        act(A.SELECT_OPTION, "department", v["department"], why="Choose the department you asked for."),
        act(A.SELECT_OPTION, "location", v["location"], why="Choose the clinic location."),
        act(A.FILL, "appointment_date", v["appointment_date"], why="Enter the date you chose."),
        act(A.CLICK, "show_slots", expected=f"visible:slot:{v['slot_time']}", why="Load the real free slots for that day."),
        act(A.CHECK, "slot", v["slot_time"], why="Pick the time slot you chose."),
        act(A.FILL, "patient_name", v["patient_name"], why="Enter the patient name."),
        act(A.CLICK, "continue_review", expected=f"route:{p}/review", why="Open the portal's review page."),
        act(A.PAUSE_FOR_CONFIRMATION, "confirm_booking", why="Booking an appointment needs your explicit approval."),
        act(A.CLICK, "confirm_booking", expected=f"route_prefix:{p}/booking/", auth=True, why="Confirm the booking you approved."),
        act(A.VERIFY_STATE, "reference", expected="db:demo_appointment", why="Check the clinic saved the booking."),
    ]


def _cancel_plan(adapter: PortalAdapter, v: dict[str, str], task_id: str) -> list[BrowserAction]:
    p = adapter.route_prefix
    ref = v["booking_reference"]
    return [
        act(A.NAVIGATE, f"{p}/booking/{ref}", expected=f"route:{p}/booking/{ref}", why="Open the demo booking page."),
        act(A.PAUSE_FOR_CONFIRMATION, "cancel_booking", why="Cancelling needs your explicit approval."),
        act(A.CLICK, "cancel_booking", expected=f"route:{p}/booking/{ref}/cancel", auth=True, why="Start cancellation."),
        act(A.CLICK, "confirm_cancel", expected=f"route:{p}/booking/{ref}", auth=True, why="Confirm cancellation you approved."),
        act(A.VERIFY_STATE, "booking_status", expected="db:demo_appointment_cancelled", why="Check the clinic recorded the cancellation."),
    ]


ADAPTER = PortalAdapter(
    portal_id="demo_clinic",
    name="GramSetu Demo Clinic Portal",
    route_prefix="/portal/clinic",
    supported_tasks=("clinic_appointment",),
    fields=FIELDS,
    field_order=("department", "location", "appointment_date", "slot_time", "patient_name"),
    targets=TARGETS,
    consequential_targets=frozenset({"confirm_booking", "cancel_booking", "confirm_cancel"}),
    completion_evidence="Booking page shows a reference AND demo_appointments holds a 'booked' row for that reference and slot.",
    plan_builder=_book_plan,
)

CANCEL_ADAPTER = PortalAdapter(
    portal_id="demo_clinic_cancel",
    name="GramSetu Demo Clinic Portal (cancellation)",
    route_prefix="/portal/clinic",
    supported_tasks=("cancel_appointment",),
    fields=CANCEL_FIELDS,
    field_order=("booking_reference",),
    targets=TARGETS,
    consequential_targets=frozenset({"cancel_booking", "confirm_cancel"}),
    completion_evidence="demo_appointments row for the reference has status 'cancelled'.",
    plan_builder=_cancel_plan,
)
