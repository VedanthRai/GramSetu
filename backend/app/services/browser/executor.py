"""Playwright executor: one isolated browser context per task, policy-checked actions, evidence-based results."""
from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable
from urllib.parse import urlparse

from playwright.async_api import Browser, BrowserContext, Locator, Page, Playwright, async_playwright

from app.core.config import DATA_DIR, get_settings
from app.core.logging import get_logger, sanitize
from app.db.database import db, now_iso
from app.portals.base import PortalAdapter
from app.schemas.contracts import ActionStatus, ActionType, BrowserAction
from app.security.guards import looks_like_injection
from app.services.browser import policy
from app.services.browser.verifier import verify

log = get_logger("gramsetu.browser")
SCREENSHOT_DIR = DATA_DIR / "screenshots"
MAX_PAGE_TEXT = 4000
ACTION_TIMEOUT_MS = 6000
Emit = Callable[..., Awaitable[None]]


class BrowserManager:
    """Single Chromium process; every task gets its own fresh context (cookies, storage isolated)."""

    def __init__(self) -> None:
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()
        self.last_error: str | None = None

    async def browser(self) -> Browser:
        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                s = get_settings()
                self._pw = self._pw or await async_playwright().start()
                self._browser = await self._pw.chromium.launch(headless=s.browser_headless,
                                                               slow_mo=0 if s.browser_headless else 350)
            return self._browser

    async def new_context(self, task_id: str) -> BrowserContext:
        b = await self.browser()
        ctx = await b.new_context(accept_downloads=False, viewport={"width": 1100, "height": 820},
                                  java_script_enabled=True, service_workers="block")
        origin = policy.allowed_origin()
        host = urlparse(origin).hostname or "127.0.0.1"
        await ctx.add_cookies([{"name": "gs_idem", "value": task_id, "domain": host, "path": "/"}])

        async def guard(route, request):  # SSRF / external navigation protection at the network layer
            u = urlparse(request.url)
            if f"{u.scheme}://{u.netloc}" != origin or not u.path.startswith("/portal/"):
                await route.abort("blockedbyclient")
            else:
                await route.continue_()

        await ctx.route("**/*", guard)
        return ctx

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        self._browser = self._pw = None


MANAGER = BrowserManager()


@dataclass
class RunState:
    cursor: int = 0
    status: str = "idle"  # running | awaiting_user_input | paused_for_confirmation | verified | failed | cancelled
    approved_final: bool = False
    error: str | None = None
    evidence: dict = field(default_factory=dict)
    recovered: list[str] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)


class BrowserRun:
    def __init__(self, session_id: str, task_id: str, adapter: PortalAdapter, plan: list[BrowserAction],
                 values: dict[str, str], emit: Emit) -> None:
        self.session_id, self.task_id, self.adapter, self.plan = session_id, task_id, adapter, plan
        self.values, self.emit = values, emit
        self.state = RunState()
        self.ctx: BrowserContext | None = None
        self.page: Page | None = None
        self._cancel = asyncio.Event()
        self._shot_n = 0

    # ------------------------------------------------------------------ helpers
    def _loc(self, action: BrowserAction) -> Locator:
        assert self.page is not None
        loc = self.adapter.targets[action.target]
        p = self.page
        if action.target == "slot":
            return p.get_by_role("radio", name=re.compile(rf"^\s*{re.escape(action.value or '')} with"))
        return {
            "label": lambda: p.get_by_label(loc.value, exact=True),
            "role_button": lambda: p.get_by_role("button", name=loc.value, exact=True),
            "role_link": lambda: p.get_by_role("link", name=loc.value, exact=True),
            "role_radio": lambda: p.get_by_role("radio", name=loc.value, exact=True),
            "role_checkbox": lambda: p.get_by_role("checkbox", name=loc.value, exact=True),
            "test_id": lambda: p.get_by_test_id(loc.value),
            "text": lambda: p.get_by_text(loc.value, exact=True),
        }[loc.kind]()

    async def _unique(self, action: BrowserAction) -> Locator:
        found = self._loc(action)
        n = await found.count()
        if n != 1:
            raise LookupError(f"Target '{action.target}' matched {n} elements; GramSetu will not guess")
        return found

    def _route(self) -> str:
        return urlparse(self.page.url).path if self.page else ""

    async def _shot(self, label: str) -> str | None:
        if not self.page:
            return None
        self._shot_n += 1
        d = SCREENSHOT_DIR / self.session_id
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{self._shot_n:03d}.png"
        mask = [self.page.locator("#otp"), self.page.locator("#mobile"), self.page.get_by_test_id("injection-probe")]
        await self.page.screenshot(path=str(path), mask=mask, mask_color="#24324a", full_page=False)
        self.state.screenshots.append(path.name)
        await self.emit("browser", "screenshot", label, {"screenshot": path.name, "route": self._route(),
                                                         "origin": policy.allowed_origin()})
        return path.name

    async def _audit(self, a: BrowserAction, detail: str, shot: str | None = None) -> None:
        with db() as c:
            c.execute("INSERT INTO browser_audit (session_id, action_id, action_type, target, origin, route, status, detail,"
                      " screenshot, at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (self.session_id, a.action_id, a.action_type.value, a.target, policy.allowed_origin(),
                       self._route(), a.status.value, sanitize(detail)[:300], shot, now_iso()))

    async def _expect(self, expected: str) -> bool:
        if not expected:
            return True
        assert self.page is not None
        deadline = time.monotonic() + ACTION_TIMEOUT_MS / 1000
        while time.monotonic() < deadline:
            try:
                await self.page.wait_for_load_state("domcontentloaded", timeout=2000)
            except Exception:
                pass
            path = self._route()
            if expected.startswith("route_prefix:") and path.startswith(expected.split(":", 1)[1]):
                return True
            if expected.startswith("route:") and path == expected.split(":", 1)[1]:
                return True
            if expected.startswith("visible:"):
                key = expected.split(":", 1)[1]
                if key.startswith("slot:"):
                    el = self._loc(BrowserAction(action_id="x", action_type=ActionType.CHECK, target="slot", value=key[5:]))
                else:
                    el = self._loc(BrowserAction(action_id="x", action_type=ActionType.FILL, target=key))
                if await el.count() == 1 and await el.is_visible():
                    return True
            if await self.page.locator("[role=alert]").count():
                return False
            await asyncio.sleep(0.15)
        return False

    async def _observe(self) -> dict:
        """Read page text as UNTRUSTED data (capped). Used only for errors and verification, never for planning."""
        assert self.page is not None
        text = (await self.page.locator("main").inner_text())[:MAX_PAGE_TEXT] if await self.page.locator("main").count() else ""
        hidden_injection = await self.page.get_by_test_id("injection-probe").count()
        alert = self.page.locator("[role=alert]")
        err_key = err_text = None
        if await alert.count():
            err_key = await alert.first.get_attribute("data-error-key")
            err_text = (await alert.first.inner_text())[:200]
        return {"text": text, "injection_present": bool(hidden_injection) or looks_like_injection(text),
                "error_key": err_key, "error_text": err_text}

    # ------------------------------------------------------------------ lifecycle
    async def start(self) -> str:
        self.ctx = await MANAGER.new_context(self.task_id)
        self.page = await self.ctx.new_page()
        self.page.set_default_timeout(ACTION_TIMEOUT_MS)
        await self.emit("browser", "context", "Browser: isolated context opened", {})
        return await self._run()

    async def approve_final(self) -> str:
        self.state.approved_final = True
        self.state.cursor += 1  # move past the PAUSE_FOR_CONFIRMATION step
        return await self._run()

    async def provide_secret(self, value: str) -> str:
        """User-typed OTP relayed straight into the portal field. Never logged, stored, spoken or sent to a model."""
        a = self.plan[self.state.cursor]
        if a.action_type != ActionType.REQUEST_USER_INPUT or self.state.status != "awaiting_user_input":
            raise RuntimeError("No user input is being requested right now")
        await (await self._unique(a)).fill(value)
        verify_btn = BrowserAction(action_id="u", action_type=ActionType.CLICK, target="verify_code")
        await (await self._unique(verify_btn)).click()
        value = ""  # drop reference immediately
        return await self.resume_manual()

    async def resume_manual(self) -> str:
        a = self.plan[self.state.cursor]
        if await self._expect(a.expected_result):
            a.status = ActionStatus.SUCCEEDED
            await self._audit(a, "user completed the step; expected state observed")
            await self.emit("user", "user_action_done", "User: completed verification (code not recorded)", {})
            self.state.cursor += 1
            return await self._run()
        obs = await self._observe()
        await self.emit("browser", "still_waiting", "Browser: expected page not reached yet",
                        {"error": obs.get("error_text")})
        self.state.status = "awaiting_user_input"
        return self.state.status

    async def cancel(self) -> list[str]:
        self._cancel.set()
        done = [a.explanation for a in self.plan if a.status == ActionStatus.SUCCEEDED and a.action_type in (
            ActionType.FILL, ActionType.SELECT_OPTION, ActionType.CHECK, ActionType.CLICK)]
        self.state.status = "cancelled"
        await self.close()
        return done

    async def close(self) -> None:
        if self.ctx:
            try:
                await self.ctx.close()
            except Exception:
                pass
        self.ctx = self.page = None

    # ------------------------------------------------------------------ main loop
    async def _run(self) -> str:
        self.state.status = "running"
        while self.state.cursor < len(self.plan):
            if self._cancel.is_set():
                self.state.status = "cancelled"
                return self.state.status
            a = self.plan[self.state.cursor]
            try:
                policy.validate(a, self.adapter, approved_final=self.state.approved_final,
                                current_url=self.page.url if self.page else None)
            except policy.PolicyViolation as e:
                a.status, a.error_message = ActionStatus.REJECTED, str(e)
                await self._audit(a, f"policy rejected: {e}")
                await self.emit("policy", "rejected", f"Policy: action rejected — {e}", {"action": a.model_dump(mode="json")})
                return await self._fail(str(e))
            a.status = ActionStatus.RUNNING
            await self.emit("browser", "action_started", a.explanation or a.action_type.value,
                            {"action": a.model_dump(mode="json", exclude={"value"} if a.target in ("mobile",) else None)})
            try:
                outcome = await self._execute(a)
            except LookupError as e:
                a.status, a.error_message = ActionStatus.FAILED, str(e)
                await self._audit(a, str(e))
                return await self._fail(str(e))
            except Exception as e:  # Playwright timeouts etc.
                a.status, a.error_message = ActionStatus.FAILED, sanitize(str(e))[:200]
                await self._audit(a, a.error_message)
                return await self._fail(f"Browser step failed: {a.explanation}")
            if outcome in ("awaiting_user_input", "paused_for_confirmation", "failed", "verified"):
                return outcome
            self.state.cursor += 1
        return await self._fail("Plan ended without verification")

    async def _fail(self, msg: str) -> str:
        self.state.status, self.state.error = "failed", msg
        if self.page:
            await self._shot("Browser: state when the task stopped")
        return "failed"

    async def _execute(self, a: BrowserAction) -> str:
        assert self.page is not None
        t = a.action_type
        if t == ActionType.NAVIGATE:
            url = policy.resolve_navigation(a.target, self.adapter)
            await self.page.goto(url, wait_until="domcontentloaded")
            obs = await self._observe()
            if obs["injection_present"]:
                await self.emit("policy", "injection_ignored",
                                "Policy: page contains instruction-like text aimed at AI agents — treated as data and ignored", {})
            ok = await self._expect(a.expected_result)
            return await self._settle(a, ok, "Browser: portal opened")
        if t == ActionType.CAPTURE_SCREENSHOT:
            a.status = ActionStatus.SUCCEEDED
            shot = await self._shot("Browser: screenshot")
            await self._audit(a, "screenshot", shot)
            return "ok"
        if t == ActionType.PAUSE_FOR_CONFIRMATION:
            existing = verify(self.adapter.portal_id, self.task_id, None, self.values, check_only=True)
            if existing.get("verified"):
                # Idempotency: the consequential step already happened (e.g. resume after timeout). Never repeat it.
                await self.emit("verifier", "already_done", "Verifier: record already exists — not submitting again", {})
                self.state.evidence = existing
                self.state.status = "verified"
                return "verified"
            a.status = ActionStatus.SUCCEEDED
            shot = await self._shot("Browser: paused for your approval")
            await self._audit(a, "paused for confirmation", shot)
            self.state.status = "paused_for_confirmation"
            return "paused_for_confirmation"
        if t == ActionType.REQUEST_USER_INPUT:
            shot = await self._shot("Browser: waiting for you to enter the code")
            await self._audit(a, "waiting for user input (secret field)", shot)
            self.state.status = "awaiting_user_input"
            return "awaiting_user_input"
        if t == ActionType.VERIFY_STATE:
            ref = None
            el = self._loc(a)
            if await el.count() == 1:
                ref = (await el.inner_text()).strip()
            ev = verify(self.adapter.portal_id, self.task_id, ref, self.values)
            shot = await self._shot("Verifier: evidence captured")
            self.state.evidence = {**ev, "screenshot": shot, "route": self._route()}
            a.status = ActionStatus.SUCCEEDED if ev["verified"] else ActionStatus.FAILED
            await self._audit(a, ev["description"], shot)
            if not ev["verified"]:
                await self.emit("verifier", "mismatch", f"Verifier: {ev['description']}", ev)
                return await self._fail(ev["description"])
            await self.emit("verifier", "verified", f"Verifier: {ev['description']}", ev)
            self.state.status = "verified"
            return "verified"
        if t == ActionType.WAIT_FOR_ELEMENT:
            await (await self._unique(a)).wait_for(state="visible")
            return await self._settle(a, True, "Browser: element ready")
        if t == ActionType.SCROLL:
            await self.page.mouse.wheel(0, 400)
            return await self._settle(a, True, "Browser: scrolled")

        loc = await self._unique(a)
        if t == ActionType.FILL:
            await loc.fill(a.value or "")
            self._entered = True
            return await self._settle(a, True, "Browser: field filled", shot=False)
        if t == ActionType.SELECT_OPTION:
            await loc.select_option(value=a.value)
            self._entered = True
            return await self._settle(a, True, "Browser: option selected", shot=False)
        if t in (ActionType.CHECK, ActionType.UNCHECK):
            await (loc.check() if t == ActionType.CHECK else loc.uncheck())
            self._entered = True
            return await self._settle(a, True, "Browser: option marked", shot=False)
        if t == ActionType.CLICK:
            if getattr(self, "_entered", False):  # show the filled form (sensitive fields masked) before moving on
                await self._shot("Browser: details entered on this page")
                self._entered = False
            await loc.click()
            ok = await self._expect(a.expected_result)
            if not ok:
                ok = await self._recover(a)
            return await self._settle(a, ok, "Browser: step completed")
        raise RuntimeError(f"Unhandled action {t}")

    async def _settle(self, a: BrowserAction, ok: bool, label: str, shot: bool = True) -> str:
        s = await self._shot(label) if shot else None
        if ok:
            a.status = ActionStatus.SUCCEEDED
            await self._audit(a, "expected state observed", s)
            await self.emit("browser", "action_succeeded", label, {"action_id": a.action_id, "target": a.target})
            return "ok"
        obs = await self._observe()
        a.status = ActionStatus.FAILED
        a.error_message = obs.get("error_text") or f"Expected '{a.expected_result}' was not observed"
        await self._audit(a, a.error_message, s)
        await self.emit("browser", "action_failed", f"Browser: {a.error_message}", {"action_id": a.action_id})
        return await self._fail(a.error_message)

    async def _recover(self, a: BrowserAction) -> bool:
        """One bounded, evidence-based recovery driven by the portal's own validation error key."""
        obs = await self._observe()
        key = obs.get("error_key")
        rule = self.adapter.recovery.get(key or "")
        if not rule or key in self.state.recovered:
            return False
        await self.emit("browser", "validation_error", f"Browser: validation error — {obs.get('error_text')}", {"error_key": key})
        await self._shot("Browser: the portal's validation error")
        if rule == "reformat_two_decimals":
            raw = self.values.get("land_area_acres", "")
            try:
                fixed = f"{float(raw):.2f}"
            except ValueError:
                return False
            fill = BrowserAction(action_id=a.action_id + "r", action_type=ActionType.FILL, target="land_area_acres",
                                 value=fixed, explanation="Re-enter land area in the format the portal asked for.")
            policy.validate(fill, self.adapter, approved_final=self.state.approved_final, current_url=self.page.url)
            await (await self._unique(fill)).fill(fixed)
            # Re-select radios: the portal re-renders them from what was submitted, but be explicit.
            for tgt in (f"ownership_{self.values['ownership']}", f"bank_{self.values['bank_account_linked']}"):
                ra = BrowserAction(action_id="r", action_type=ActionType.CHECK, target=tgt)
                await (await self._unique(ra)).check()
            self.state.recovered.append(key)
            await self._shot(f"Browser: corrected value entered ({fixed})")
            await (await self._unique(a)).click()
            ok = await self._expect(a.expected_result)
            if ok:
                await self.emit("browser", "recovered", f"Browser: validation error, recovered (entered {fixed})", {"error_key": key})
            return ok
        return False
