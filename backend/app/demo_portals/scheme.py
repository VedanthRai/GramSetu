"""Demo scheme portal (PM-KISAN-style). Multi-step real HTML forms, server-side validation, demo OTP."""
from __future__ import annotations

import re
import secrets

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.db.database import db, dumps, now_iso
from app.demo_portals.common import DEMO_SMS, PORTAL_SESSIONS, esc, idempotency_key, page
from app.portals.demo_scheme import DISTRICT_LABEL, DISTRICTS, STATE_LABEL

router = APIRouter(prefix="/portal/scheme", include_in_schema=False)
TITLE = "Kisan Income Support — Demo Application"
SUB = "Practice portal for GramSetu demonstrations. Records created here are demo records only."


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


def _steps(active: int) -> str:
    names = ["Applicant", "Land", "Verify mobile", "Review"]
    return '<div class="steps">' + " › ".join(f"<b>{n}</b>" if i == active else n for i, n in enumerate(names)) + "</div>"


@router.get("/", response_class=HTMLResponse)
def start(request: Request) -> HTMLResponse:
    return _html(request, """
<p>This practice form mirrors the kind of information a farmer income-support application asks for.
It is <b>not</b> connected to any government system.</p>
<form method="post" action="/portal/scheme/start"><button type="submit">Start demo application</button></form>""")


@router.post("/start")
def do_start(request: Request) -> RedirectResponse:
    sid, s, new = _sess(request)
    s.clear()
    r = RedirectResponse("/portal/scheme/applicant", status_code=303)
    if new:
        r.set_cookie("gs_portal", sid, httponly=True, samesite="lax")
    return r


def _applicant_form(s: dict, error: str = "") -> str:
    a = s.get("applicant", {})
    opts_state = "".join(f'<option value="{k}"{" selected" if a.get("state") == k else ""}>{v}</option>'
                         for k, v in STATE_LABEL.items())
    opts_district = "".join(
        f'<optgroup label="{STATE_LABEL[st]}">' + "".join(
            f'<option value="{d}"{" selected" if a.get("district") == d else ""}>{DISTRICT_LABEL[d]}</option>' for d in ds)
        + "</optgroup>" for st, ds in DISTRICTS.items())
    err = f'<div class="err" role="alert" data-error-key="applicant">{esc(error)}</div>' if error else ""
    return f"""{_steps(0)}<h2>Applicant details</h2>{err}
<form method="post" action="/portal/scheme/applicant">
<label for="full_name">Applicant full name</label><input type="text" id="full_name" name="full_name" value="{esc(a.get('full_name',''))}" autocomplete="off">
<label for="state">State</label><select id="state" name="state"><option value="">— choose —</option>{opts_state}</select>
<label for="district">District</label><select id="district" name="district"><option value="">— choose —</option>{opts_district}</select>
<label for="village">Village</label><input type="text" id="village" name="village" value="{esc(a.get('village',''))}" autocomplete="off">
<button type="submit">Save and continue to land details</button></form>"""


@router.get("/applicant", response_class=HTMLResponse)
def applicant(request: Request) -> HTMLResponse:
    _, s, _ = _sess(request)
    return _html(request, _applicant_form(s))


@router.post("/applicant", response_class=HTMLResponse)
def applicant_post(request: Request, full_name: str = Form(""), state: str = Form(""), district: str = Form(""),
                   village: str = Form("")):
    _, s, _ = _sess(request)
    s["applicant"] = {"full_name": full_name.strip()[:80], "state": state, "district": district, "village": village.strip()[:60]}
    if not full_name.strip() or not village.strip():
        return _html(request, _applicant_form(s, "Name and village are required."), 422)
    if state not in DISTRICTS:
        return _html(request, _applicant_form(s, "Please choose a state."), 422)
    if district not in DISTRICTS[state]:
        return _html(request, _applicant_form(s, "The selected district does not belong to the selected state."), 422)
    return RedirectResponse("/portal/scheme/land", status_code=303)


def _land_form(s: dict, error: str = "", key: str = "") -> str:
    land = s.get("land", {})

    def chk(n: str, v: str) -> str:
        return " checked" if land.get(n) == v else ""
    err = f'<div class="err" role="alert" data-error-key="{key}">{esc(error)}</div>' if error else ""
    return f"""{_steps(1)}<h2>Land details</h2>{err}
<form method="post" action="/portal/scheme/land">
<label for="land_area_acres">Land area in acres</label><input type="text" inputmode="decimal" id="land_area_acres" name="land_area_acres" value="{esc(land.get('land_area_acres',''))}">
<p class="muted">Format: number with two decimal places.</p>
<fieldset><legend>How is the land held?</legend>
<label><input type="radio" name="ownership" value="owner"{chk('ownership','owner')}> Land is in my own name</label>
<label><input type="radio" name="ownership" value="tenant"{chk('ownership','tenant')}> I farm as a tenant</label></fieldset>
<fieldset><legend>Bank account</legend>
<label><input type="radio" name="bank" value="yes"{chk('bank','yes')}> Yes, I have a bank account</label>
<label><input type="radio" name="bank" value="no"{chk('bank','no')}> No bank account</label></fieldset>
<button type="submit">Save and continue to verification</button></form>"""


@router.get("/land", response_class=HTMLResponse)
def land(request: Request) -> HTMLResponse:
    _, s, _ = _sess(request)
    if "applicant" not in s:
        return RedirectResponse("/portal/scheme/", status_code=303)
    return _html(request, _land_form(s))


@router.post("/land", response_class=HTMLResponse)
def land_post(request: Request, land_area_acres: str = Form(""), ownership: str = Form(""), bank: str = Form("")):
    _, s, _ = _sess(request)
    s["land"] = {"land_area_acres": land_area_acres.strip(), "ownership": ownership, "bank": bank}
    # Deliberately strict format: rejects "2" so the demo can show safe, evidence-based recovery.
    if not re.fullmatch(r"\d{1,3}\.\d{2}", land_area_acres.strip()):
        return _html(request, _land_form(s, "Enter the land area with two decimal places, for example 2.00", "land_area_format"), 422)
    if not 0 < float(land_area_acres) <= 100:
        return _html(request, _land_form(s, "Land area must be between 0.01 and 100 acres.", "land_area_range"), 422)
    if ownership not in ("owner", "tenant") or bank not in ("yes", "no"):
        return _html(request, _land_form(s, "Please answer both questions.", "land_choice"), 422)
    return RedirectResponse("/portal/scheme/verify", status_code=303)


def _verify_form(s: dict, error: str = "") -> str:
    sent = s.get("otp_sent")
    err = f'<div class="err" role="alert" data-error-key="otp">{esc(error)}</div>' if error else ""
    otp_part = ""
    if sent:
        otp_part = """<form method="post" action="/portal/scheme/verify/check">
<p class="ok">A demo verification code was sent to the simulated phone in the GramSetu app.</p>
<label for="otp">Verification code</label><input type="password" inputmode="numeric" autocomplete="one-time-code" id="otp" name="otp" maxlength="6">
<button type="submit">Verify code</button></form>"""
    return f"""{_steps(2)}<h2>Verify mobile</h2>{err}
<form method="post" action="/portal/scheme/verify/send">
<label for="mobile">Mobile number (demo)</label><input type="tel" id="mobile" name="mobile" value="{esc(s.get('mobile',''))}" autocomplete="off">
<button type="submit">Send verification code</button></form>{otp_part}"""


@router.get("/verify", response_class=HTMLResponse)
def verify(request: Request) -> HTMLResponse:
    _, s, _ = _sess(request)
    if "land" not in s:
        return RedirectResponse("/portal/scheme/", status_code=303)
    return _html(request, _verify_form(s))


@router.post("/verify/send", response_class=HTMLResponse)
def verify_send(request: Request, mobile: str = Form("")):
    sid, s, _ = _sess(request)
    digits = re.sub(r"\D", "", mobile)
    s["mobile"] = digits
    if not re.fullmatch(r"[6-9]\d{9}", digits):
        return _html(request, _verify_form(s, "Enter a 10-digit mobile number."), 422)
    code = f"{secrets.randbelow(10**6):06d}"
    s["otp"], s["otp_sent"], s["otp_ok"] = code, True, False
    DEMO_SMS[sid] = {"to": f"******{digits[-4:]}", "code": code, "text": "Demo portal verification code (never share it)"}
    return _html(request, _verify_form(s))


@router.post("/verify/check", response_class=HTMLResponse)
def verify_check(request: Request, otp: str = Form("")):
    sid, s, _ = _sess(request)
    if not s.get("otp_sent") or otp.strip() != s.get("otp"):
        return _html(request, _verify_form(s, "That code is not correct."), 422)
    s["otp_ok"] = True
    s.pop("otp", None)
    DEMO_SMS.pop(sid, None)
    return RedirectResponse("/portal/scheme/review", status_code=303)


def _review(s: dict, error: str = "") -> str:
    a, land = s["applicant"], s["land"]
    err = f'<div class="err" role="alert">{esc(error)}</div>' if error else ""
    rows = [("Applicant", a["full_name"]), ("State", STATE_LABEL[a["state"]]), ("District", DISTRICT_LABEL[a["district"]]),
            ("Village", a["village"]), ("Land area (acres)", land["land_area_acres"]),
            ("Ownership", "Own name" if land["ownership"] == "owner" else "Tenant"),
            ("Bank account", "Yes" if land["bank"] == "yes" else "No"), ("Mobile", "******" + s["mobile"][-4:])]
    table = "".join(f"<tr><td>{k}</td><td>{esc(v)}</td></tr>" for k, v in rows)
    return f"""{_steps(3)}<h2>Review</h2>{err}<table data-testid="review-table">{table}</table>
<form method="post" action="/portal/scheme/submit">
<fieldset><legend>Declaration</legend><label><input type="checkbox" name="declaration" value="yes"> I declare that the details above are correct (demo declaration)</label></fieldset>
<button type="submit">Submit demo application</button></form>"""


@router.get("/review", response_class=HTMLResponse)
def review(request: Request) -> HTMLResponse:
    _, s, _ = _sess(request)
    if not s.get("otp_ok"):
        return RedirectResponse("/portal/scheme/verify", status_code=303)
    return _html(request, _review(s))


@router.post("/submit", response_class=HTMLResponse)
def submit(request: Request, declaration: str = Form("")):
    _, s, _ = _sess(request)
    if not s.get("otp_ok"):
        return RedirectResponse("/portal/scheme/verify", status_code=303)
    if declaration != "yes":
        return _html(request, _review(s, "Please accept the declaration."), 422)
    key = idempotency_key(request)
    data = {"applicant": s["applicant"], "land": s["land"], "mobile_last4": s["mobile"][-4:]}
    with db() as c:
        row = c.execute("SELECT reference FROM demo_applications WHERE idempotency_key=?", (key,)).fetchone()
        if row:
            ref = row["reference"]
        else:
            ref = "GS-SC-" + secrets.token_hex(3).upper()
            c.execute("INSERT INTO demo_applications VALUES (?,?,?,?)", (ref, dumps(data), now_iso(), key))
    return RedirectResponse(f"/portal/scheme/confirmation/{ref}", status_code=303)


@router.get("/confirmation/{ref}", response_class=HTMLResponse)
def confirmation(request: Request, ref: str) -> HTMLResponse:
    with db() as c:
        row = c.execute("SELECT reference, created_at FROM demo_applications WHERE reference=?", (ref,)).fetchone()
    if not row:
        return _html(request, '<div class="err" role="alert">No such demo application.</div>', 404)
    return _html(request, f"""<div class="ok"><h2>Demo application stored</h2>
<p>Demo reference: <b data-testid="application-reference">{esc(row['reference'])}</b></p>
<p>Stored at {esc(row['created_at'])}.</p>
<p><b>DEMO RECORD — this is not an official application and has not been sent to any government system.</b></p></div>""")
