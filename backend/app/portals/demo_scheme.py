"""Adapter for the locally hosted demo scheme portal (PM-KISAN-style form; NOT an official site)."""
from __future__ import annotations

from app.portals.base import FieldSpec, Locator, PortalAdapter, act
from app.schemas.contracts import ActionType as A
from app.schemas.contracts import BrowserAction, Sensitivity

STATES = ("karnataka", "uttar_pradesh", "tamil_nadu", "maharashtra")
DISTRICTS: dict[str, tuple[str, ...]] = {
    "karnataka": ("bengaluru_urban", "bengaluru_rural", "mysuru", "belagavi"),
    "uttar_pradesh": ("lucknow", "varanasi", "kanpur_nagar", "kanpur_dehat"),
    "tamil_nadu": ("chennai", "coimbatore", "madurai"),
    "maharashtra": ("pune", "nashik"),
}
ALL_DISTRICTS = tuple(d for ds in DISTRICTS.values() for d in ds)
# Spoken place names that map to more than one district -> GramSetu must ask, never guess.
AMBIGUOUS_PLACES = {"bengaluru": ("bengaluru_urban", "bengaluru_rural"), "kanpur": ("kanpur_nagar", "kanpur_dehat")}
DISTRICT_LABEL = {
    "bengaluru_urban": "Bengaluru Urban", "bengaluru_rural": "Bengaluru Rural", "mysuru": "Mysuru",
    "belagavi": "Belagavi", "lucknow": "Lucknow", "varanasi": "Varanasi", "kanpur_nagar": "Kanpur Nagar",
    "kanpur_dehat": "Kanpur Dehat", "chennai": "Chennai", "coimbatore": "Coimbatore", "madurai": "Madurai",
    "pune": "Pune", "nashik": "Nashik",
}
STATE_LABEL = {"karnataka": "Karnataka", "uttar_pradesh": "Uttar Pradesh", "tamil_nadu": "Tamil Nadu",
               "maharashtra": "Maharashtra"}
STATE_OF = {d: s for s, ds in DISTRICTS.items() for d in ds}

FIELDS = {
    "full_name": FieldSpec("full_name", "text", sensitivity=Sensitivity.PERSONAL, ask_key="ask.full_name"),
    "state": FieldSpec("state", "select", options=STATES, ask_key="ask.state"),
    "district": FieldSpec("district", "select", options=ALL_DISTRICTS, ask_key="ask.district"),
    "village": FieldSpec("village", "text", ask_key="ask.village"),
    "land_area_acres": FieldSpec("land_area_acres", "number", ask_key="ask.land_area_acres"),
    "ownership": FieldSpec("ownership", "radio", options=("owner", "tenant"), ask_key="ask.ownership"),
    "bank_account_linked": FieldSpec("bank_account_linked", "radio", options=("yes", "no"), ask_key="ask.bank_account_linked"),
    "mobile": FieldSpec("mobile", "text", sensitivity=Sensitivity.PERSONAL, ask_key="ask.mobile"),
}

TARGETS = {
    "start_application": Locator("role_button", "Start demo application"),
    "full_name": Locator("label", "Applicant full name"),
    "state": Locator("label", "State"),
    "district": Locator("label", "District"),
    "village": Locator("label", "Village"),
    "next_applicant": Locator("role_button", "Save and continue to land details"),
    "land_area_acres": Locator("label", "Land area in acres"),
    "ownership_owner": Locator("role_radio", "Land is in my own name"),
    "ownership_tenant": Locator("role_radio", "I farm as a tenant"),
    "bank_yes": Locator("role_radio", "Yes, I have a bank account"),
    "bank_no": Locator("role_radio", "No bank account"),
    "next_land": Locator("role_button", "Save and continue to verification"),
    "mobile": Locator("label", "Mobile number (demo)"),
    "send_code": Locator("role_button", "Send verification code"),
    "otp": Locator("label", "Verification code"),
    "verify_code": Locator("role_button", "Verify code"),
    "declaration": Locator("role_checkbox", "I declare that the details above are correct (demo declaration)"),
    "submit_application": Locator("role_button", "Submit demo application"),
    "reference": Locator("test_id", "application-reference"),
}


def _plan(adapter: PortalAdapter, v: dict[str, str], task_id: str) -> list[BrowserAction]:
    p = adapter.route_prefix
    return [
        act(A.NAVIGATE, f"{p}/", expected=f"route:{p}/", why="Open the demo scheme portal start page."),
        act(A.CAPTURE_SCREENSHOT, why="Show you the portal before anything is entered."),
        act(A.CLICK, "start_application", expected=f"route:{p}/applicant", why="Begin a new demo application."),
        act(A.FILL, "full_name", v["full_name"], why="Enter the applicant name you gave."),
        act(A.SELECT_OPTION, "state", v["state"], why="Choose the state you told me."),
        act(A.SELECT_OPTION, "district", v["district"], why="Choose the district you confirmed."),
        act(A.FILL, "village", v["village"], why="Enter your village name."),
        act(A.CLICK, "next_applicant", expected=f"route:{p}/land", why="Save applicant details and continue."),
        act(A.FILL, "land_area_acres", v["land_area_acres"], why="Enter the land area you told me."),
        act(A.CHECK, f"ownership_{v['ownership']}", why="Mark how the land is held, as you said."),
        act(A.CHECK, f"bank_{v['bank_account_linked']}", why="Record whether you have a bank account."),
        act(A.CLICK, "next_land", expected=f"route:{p}/verify", why="Save land details and continue."),
        act(A.FILL, "mobile", v["mobile"], why="Enter the demo mobile number for verification."),
        act(A.CLICK, "send_code", expected="visible:otp", why="Ask the demo portal to send a one-time code."),
        act(A.REQUEST_USER_INPUT, "otp", expected=f"route:{p}/review",
            why="Only you may enter a one-time code. GramSetu never reads, stores or sends it."),
        act(A.PAUSE_FOR_CONFIRMATION, "submit_application", why="Final submission needs your explicit approval."),
        act(A.CHECK, "declaration", auth=True, why="Accept the demo declaration, which you approved."),
        act(A.CLICK, "submit_application", expected=f"route_prefix:{p}/confirmation/", auth=True,
            why="Submit the demo application, which you approved."),
        act(A.VERIFY_STATE, "reference", expected="db:demo_application",
            why="Check the portal stored a record before saying it is done."),
    ]


ADAPTER = PortalAdapter(
    portal_id="demo_scheme",
    name="GramSetu Demo Scheme Portal",
    route_prefix="/portal/scheme",
    supported_tasks=("scheme_application",),
    fields=FIELDS,
    field_order=("full_name", "state", "district", "village", "land_area_acres", "ownership", "bank_account_linked", "mobile"),
    targets=TARGETS,
    secret_targets=frozenset({"otp"}),
    consequential_targets=frozenset({"declaration", "submit_application"}),
    completion_evidence="Confirmation page shows a reference AND demo_applications holds a row with that reference and this task's idempotency key.",
    plan_builder=_plan,
    recovery={"land_area_format": "reformat_two_decimals"},
)
