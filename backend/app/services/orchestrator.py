"""Session orchestrator: guards -> reasoning -> validated task -> clarification / review -> approval -> browser -> verify."""
from __future__ import annotations

import asyncio
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import db, dumps, now_iso, today_local
from app.portals.demo_scheme import AMBIGUOUS_PLACES, DISTRICTS, STATE_OF
from app.portals.registry import TASK_TO_PORTAL, get_adapter
from app.schemas.contracts import ExtractedField, Intent, ReasoningOutput, Sensitivity, SourceType, TaskIntent
from app.security import guards
from app.services import events, i18n
from app.services.appointments import service as appt
from app.services.browser.executor import BrowserRun
from app.services.reasoning.base import DialogueContext, ReasoningFailure
from app.services.reasoning.rules import RulesReasoner
from app.services.state_machine import State, check_transition, is_dialogue_state, is_terminal

log = get_logger("gramsetu.orchestrator")
S = State
MAX_SLOT_OFFERS = 4


@dataclass
class Task:
    task_id: str
    intent: str
    portal_id: str
    fields: dict[str, ExtractedField] = field(default_factory=dict)
    expected_field: str | None = None
    offered: dict[str, list[str]] = field(default_factory=dict)
    guidance_given: bool = False
    result: dict | None = None
    plan: list[dict] = field(default_factory=list)


@dataclass
class Session:
    id: str
    language: str
    state: State = S.IDLE
    retain_history: bool = False
    task: Task | None = None
    messages: list[dict] = field(default_factory=list)
    run: BrowserRun | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_turn: dict = field(default_factory=dict)
    summary_card: dict | None = None


SESSIONS: dict[str, Session] = {}


class SessionError(RuntimeError):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


class Orchestrator:
    def __init__(self, reasoner) -> None:
        self.reasoner = reasoner
        self.rules = RulesReasoner()

    # ------------------------------------------------------------ session basics
    def create_session(self, language: str, retain_history: bool = False) -> Session:
        sid = uuid.uuid4().hex
        s = Session(id=sid, language=language, retain_history=retain_history)
        SESSIONS[sid] = s
        with db() as c:
            c.execute("INSERT INTO sessions (id, created_at, language, state, retain_history) VALUES (?,?,?,?,?)",
                      (sid, now_iso(), language, s.state.value, int(retain_history)))
        self._say(s, "greeting")
        return s

    def get(self, sid: str) -> Session:
        s = SESSIONS.get(sid)
        if not s:
            raise SessionError("Session not found", 404)
        return s

    async def _transition(self, s: Session, target: State) -> None:
        prev = s.state
        s.state = check_transition(prev, target)
        with db() as c:
            c.execute("UPDATE sessions SET state=? WHERE id=?", (s.state.value, s.id))
            c.execute("INSERT INTO task_states (session_id, from_state, to_state, at) VALUES (?,?,?,?)",
                      (s.id, prev.value, target.value, now_iso()))
        await events.broadcast(s.id, {"type": "state", "state": s.state.value, "from": prev.value})

    def _say(self, s: Session, key: str, kind: str = "info", **kw) -> dict:
        text = i18n.t(key, s.language, **kw)
        return self._add_message(s, "assistant", text, kind)

    def _add_message(self, s: Session, role: str, text: str, kind: str = "info", extra: dict | None = None) -> dict:
        m = {"id": uuid.uuid4().hex[:10], "role": role, "text": text, "kind": kind, "lang": s.language,
             "at": now_iso(), **(extra or {})}
        s.messages.append(m)
        retain = s.retain_history or get_settings().retain_transcripts
        events.emit_nowait(s.id, "gramsetu" if role == "assistant" else "user", "message", f"{role} message",
                           {"message": m}, persist_data=retain)
        return m

    # ------------------------------------------------------------ context for reasoning
    def _context(self, s: Session) -> DialogueContext:
        today = today_local()
        t = s.task
        allowed: dict[str, list[str]] = {}
        if t:
            adapter = get_adapter(t.portal_id)
            allowed = {n: list(f.options) for n, f in adapter.fields.items() if f.options}
        return DialogueContext(language=s.language, today_iso=today.isoformat(), weekday=today.strftime("%A"),
                               current_intent=t.intent if t else None, expected_field=t.expected_field if t else None,
                               known_field_names=sorted(t.fields) if t else [],
                               offered_options=dict(t.offered) if t else {}, allowed_values=allowed)

    # ------------------------------------------------------------ main turn
    async def handle_turn(self, sid: str, text: str, raw_transcript: str | None = None,
                          choice: dict | None = None) -> dict:
        s = self.get(sid)
        async with s.lock:
            text = (text or "").strip()[:1000]
            if not text:
                raise SessionError("Empty turn", 400)
            if is_terminal(s.state):
                await self._transition(s, S.IDLE)
                s.task = None
            final_wait = s.state == S.PAUSED_FOR_CONFIRMATION
            if not (is_dialogue_state(s.state) or final_wait):
                raise SessionError(f"GramSetu is busy ({s.state.value}). Wait or press Stop.")
            t0 = time.perf_counter()

            # --- deterministic guards first: secrets never reach a model or a log
            if guards.is_secret_or_scam(text):
                self._add_message(s, "user", "[withheld — looked like a code, PIN or bank detail]", "withheld")
                await events.emit(s.id, "guard", "scam_warning", "Guard: possible OTP/PIN/bank-detail sharing — not processed")
                self._say(s, "scam", "warning")
                return self._turn_result(s, t0, intent="secret_sharing_risk")
            self._add_message(s, "user", text, "transcript", {"raw_transcript": raw_transcript} if raw_transcript and raw_transcript != text else None)
            if guards.is_emergency(text):
                await events.emit(s.id, "guard", "emergency", "Guard: possible emergency — booking flow stopped")
                if s.task:
                    s.task = None
                if s.state != S.IDLE:
                    await self._transition(s, S.CANCELLED)
                    await self._transition(s, S.IDLE)
                self._say(s, "emergency", "emergency")
                return self._turn_result(s, t0, intent="emergency")
            if final_wait:
                return await self._final_wait_turn(s, text, t0)

            prev_state = s.state
            await self._transition(s, S.INTERPRETING)
            ctx = self._context(s)
            r0 = time.perf_counter()
            provider_label = self.reasoner.label
            if choice and s.task:
                # The user tapped an option GramSetu offered: structured input, no interpretation needed.
                out = ReasoningOutput(intent=Intent.PROVIDE_INFO, fields=[ExtractedField(
                    field_name=choice["field"], normalized_value=choice["value"], original_user_expression=text[:300])],
                    is_correction=choice["field"] in s.task.fields)
                await events.emit(s.id, "user", "choice", f"User: selected an option for {choice['field']}")
                return await self._apply(s, out, text, None, t0, 0, prev_state)
            try:
                out = await self.reasoner.interpret(text, ctx)
            except ReasoningFailure as e:
                await events.emit(s.id, "reasoning", "error", f"Reasoning: {e}")
                await self._back_to_dialogue(s)
                self._say(s, "rephrase", "warning")
                return self._turn_result(s, t0, intent="error", reasoning_ms=int((time.perf_counter() - r0) * 1000))
            reasoning_ms = int((time.perf_counter() - r0) * 1000)
            # The local mobile extractor runs regardless of provider (numbers are redacted before any model call).
            mobile = guards.extract_mobile(text)
            await events.emit(s.id, "reasoning", "interpreted", f"Reasoning: intent identified — {out.intent.value}",
                              {"provider": provider_label, "intent": out.intent.value,
                               "fields": [f.field_name for f in out.fields], "latency_ms": reasoning_ms})
            if guards.asks_medical_advice(text):
                self._say(s, "medical_boundary", "boundary")
            return await self._apply(s, out, text, mobile, t0, reasoning_ms, prev_state)

    async def _back_to_dialogue(self, s: Session) -> None:
        if s.task is None:
            await self._transition(s, S.IDLE)
        else:
            await self._transition(s, S.NEEDS_CLARIFICATION)

    def _turn_result(self, s: Session, t0: float, **kw) -> dict:
        s.last_turn = {"server_ms": int((time.perf_counter() - t0) * 1000), **kw}
        return {"session": self.snapshot(s), "turn": s.last_turn}

    # ------------------------------------------------------------ applying model output
    async def _apply(self, s: Session, out, text: str, mobile: str | None, t0: float, reasoning_ms: int,
                     prev_state: State) -> dict:
        intent = out.intent
        if intent == Intent.EMERGENCY:
            s.task = None
            await self._transition(s, S.IDLE)
            self._say(s, "emergency", "emergency")
            return self._turn_result(s, t0, intent="emergency", reasoning_ms=reasoning_ms)
        if intent == Intent.SECRET_SHARING_RISK:
            await self._back_to_dialogue(s)
            self._say(s, "scam", "warning")
            return self._turn_result(s, t0, intent="secret_sharing_risk", reasoning_ms=reasoning_ms)

        new_task_intents = {Intent.SCHEME_APPLICATION: "scheme_application", Intent.CLINIC_APPOINTMENT: "clinic_appointment",
                            Intent.CANCEL_APPOINTMENT: "cancel_appointment"}
        if intent in new_task_intents and (s.task is None or s.task.intent != new_task_intents[intent]):
            name = new_task_intents[intent]
            s.task = Task(task_id=uuid.uuid4().hex[:16], intent=name, portal_id=TASK_TO_PORTAL[name])
            with db() as c:
                c.execute("INSERT INTO tasks (id, session_id, intent, portal_id, created_at, status) VALUES (?,?,?,?,?,?)",
                          (s.task.task_id, s.id, name, s.task.portal_id, now_iso(), "open"))
        if s.task is None:
            await self._transition(s, S.IDLE)
            self._say(s, "unsupported", "question")
            return self._turn_result(s, t0, intent=intent.value, reasoning_ms=reasoning_ms)

        t = s.task
        changes = self._merge(s, out.fields, out.is_correction)
        if mobile and t.intent == "scheme_application":
            t.fields["mobile"] = ExtractedField(field_name="mobile", normalized_value=mobile, original_user_expression="[typed number]",
                                                source_type=SourceType.USER_SPOKEN, sensitivity_level=Sensitivity.PERSONAL)
            changes.append("mobile")
        for ch in changes:
            if out.is_correction and ch in t.fields:
                self._say(s, "correction.applied", "correction", field=i18n.label(ch, s.language),
                          value=self._display_value(ch, t.fields[ch].normalized_value, s.language))
        if changes:
            await events.emit(s.id, "gramsetu", "fields_updated", f"GramSetu: {len(changes)} field(s) updated",
                              {"fields": changes, "correction": out.is_correction})

        # Confirmation / denial at the review step (voice "yes" moves review -> consent; never executes on its own)
        missing = self._missing(s)
        if not missing and not changes and intent == Intent.CONFIRM and prev_state in (S.PREVIEWING_TASK, S.AWAITING_CONSENT):
            await self._transition(s, S.PREVIEWING_TASK)
            await self._transition(s, S.AWAITING_CONSENT)
            if prev_state == S.PREVIEWING_TASK:
                await events.emit(s.id, "user", "review_confirmed", "User: confirmed the review summary (voice)")
                self._say(s, "consent.ask", "consent")
            else:
                await self._start_locked(s, via="voice")
            return self._turn_result(s, t0, intent=intent.value, reasoning_ms=reasoning_ms)
        if not missing and not changes and intent == Intent.DENY:
            await self._transition(s, S.NEEDS_CLARIFICATION)
            self._say(s, "review.ask", "question")
            return self._turn_result(s, t0, intent=intent.value, reasoning_ms=reasoning_ms)

        return await self._next_question_or_review(s, t0, intent.value, reasoning_ms)

    async def _next_question_or_review(self, s: Session, t0: float, intent: str, reasoning_ms: int) -> dict:
        t = s.task
        assert t is not None
        if t.intent == "scheme_application" and not t.guidance_given:
            t.guidance_given = True
            self._add_message(s, "assistant", i18n.t("scheme.guidance", s.language), "guidance",
                              {"sources": ["pmk-2", "pmk-3", "pmk-4", "pmk-10"], "source_url": "https://pmkisan.gov.in/"})
        missing = self._missing(s)
        if missing:
            f = missing[0]
            t.expected_field = f
            await self._transition(s, S.NEEDS_CLARIFICATION)
            await events.emit(s.id, "gramsetu", "missing_field", f"GramSetu: missing field detected — {f}", {"field": f})
            self._ask(s, f)
        else:
            t.expected_field = None
            await self._transition(s, S.PREVIEWING_TASK)
            lines = self.summary_lines(s)
            self._add_message(s, "assistant", i18n.t("review.intro", s.language, portal=i18n.PORTAL_NAMES.get(
                t.portal_id, i18n.PORTAL_NAMES["demo_clinic"]).get(s.language, t.portal_id))
                + "\n" + "\n".join(f"• {ln['label']}: {ln['value']}" for ln in lines)
                + "\n" + i18n.t("review.ask", s.language), "review", {"summary": lines})
            await events.emit(s.id, "gramsetu", "review_ready", "GramSetu: review summary ready")
        return self._turn_result(s, t0, intent=intent, reasoning_ms=reasoning_ms)

    def _ask(self, s: Session, f: str) -> None:
        t = s.task
        lang = s.language
        if f == "district_ambiguous":
            place = t.fields["district_ambiguous"].normalized_value
            opts = list(AMBIGUOUS_PLACES.get(place, ()))
            t.offered["district"] = opts
            t.expected_field = "district"
            self._add_message(s, "assistant", i18n.t("ask.district_ambiguous", lang, place=i18n.value_label(place, lang),
                              options=", ".join(i18n.value_label(o, lang) for o in opts)), "question",
                              {"field": "district", "choices": [{"value": o, "label": i18n.value_label(o, lang)} for o in opts]})
            return
        if f == "slot_time":
            pref = t.fields.get("time_preference")
            period = pref.normalized_value if pref else "any"
            day = t.fields["appointment_date"].normalized_value
            slots = appt.free_slots(t.fields["department"].normalized_value, t.fields["location"].normalized_value, day, period)
            if not slots and period != "any":
                slots = []
            if not slots:
                t.fields.pop("appointment_date", None)
                t.offered.pop("slot_time", None)
                t.expected_field = "appointment_date"
                self._add_message(s, "assistant", i18n.t("ask.no_slots", lang, date=i18n.format_date(day, lang),
                                  period=i18n.value_label(period, lang)), "question", {"field": "appointment_date"})
                return
            times = list(dict.fromkeys(x["slot_time"] for x in slots))[:MAX_SLOT_OFFERS]
            t.offered["slot_time"] = times
            self._add_message(s, "assistant", i18n.t("ask.slot_time", lang, date=i18n.format_date(day, lang),
                              options=", ".join(times)), "question",
                              {"field": "slot_time", "choices": [{"value": x, "label": x} for x in times]})
            return
        spec = get_adapter(t.portal_id).fields.get(f)
        choices = None
        if spec and spec.options and spec.kind in ("select", "radio"):
            opts = spec.options
            if f == "district" and "state" in t.fields:
                opts = DISTRICTS.get(t.fields["state"].normalized_value, opts)
            choices = [{"value": o, "label": i18n.value_label(o, lang)} for o in opts]
        self._add_message(s, "assistant", i18n.t(spec.ask_key if spec and spec.ask_key else f"ask.{f}", lang), "question",
                          {"field": f, "choices": choices, "secure_typing": f == "mobile"})

    # ------------------------------------------------------------ field validation
    def _merge(self, s: Session, fields: list[ExtractedField], is_correction: bool) -> list[str]:
        t = s.task
        assert t is not None
        adapter = get_adapter(t.portal_id)
        changed: list[str] = []
        today = today_local()
        for f in fields:
            name, val = f.field_name, f.normalized_value.strip()
            if name == "district_ambiguous":
                if val in AMBIGUOUS_PLACES and "district" not in t.fields:
                    t.fields[name] = f
                    changed.append(name)
                continue
            spec = adapter.fields.get(name)
            if spec is None or spec.kind == "derived" or not val:
                continue  # model proposed a field this portal does not have: ignore
            if spec.sensitivity == Sensitivity.SECRET:
                continue
            if spec.options and name != "slot_time" and val not in spec.options:
                continue
            if name == "land_area_acres":
                try:
                    x = float(val)
                except ValueError:
                    continue
                if not 0 < x <= 100:
                    continue
                val = f"{x:g}"
            if name == "appointment_date":
                try:
                    d = date.fromisoformat(val)
                except ValueError:
                    continue
                if d < today or d > today + timedelta(days=20):
                    continue
                if "appointment_date" in t.fields and t.fields["appointment_date"].normalized_value != val:
                    t.fields.pop("slot_time", None)
                    t.fields.pop("doctor", None)
                    t.offered.pop("slot_time", None)
            if name == "slot_time":
                if not re.fullmatch(r"\d{2}:\d{2}", val):
                    continue
                needed = ("department", "location", "appointment_date")
                if not all(k in t.fields for k in needed):
                    continue
                slot = appt.find_slot(t.fields["department"].normalized_value, t.fields["location"].normalized_value,
                                      t.fields["appointment_date"].normalized_value, val)
                if not slot or slot["booked"]:
                    continue  # only slots that actually exist and are free
                t.fields["doctor"] = ExtractedField(field_name="doctor", normalized_value=slot["doctor"],
                                                    source_type=SourceType.DERIVED)
            if name == "booking_reference":
                b = appt.get_booking(val.upper())
                if not b or b["status"] != "booked":
                    continue
                val = val.upper()
            if name in ("full_name", "patient_name", "village"):
                val = re.sub(r"[<>{}\[\]\\/]", "", val)[:80]
                if len(val) < 2:
                    continue
            if name in ("department", "location") and name in t.fields and t.fields[name].normalized_value != val:
                t.fields.pop("slot_time", None)
                t.offered.pop("slot_time", None)
            existing = t.fields.get(name)
            if existing and existing.normalized_value == val:
                continue
            src = SourceType.USER_CORRECTED if (is_correction and existing) else f.source_type
            t.fields[name] = ExtractedField(field_name=name, normalized_value=val,
                                            original_user_expression=f.original_user_expression[:300],
                                            source_type=src, sensitivity_level=spec.sensitivity)
            changed.append(name)
            if name == "district":
                t.fields.pop("district_ambiguous", None)
                t.offered.pop("district", None)
                st = STATE_OF.get(val)
                if st and ("state" not in t.fields or t.fields["state"].normalized_value != st):
                    t.fields["state"] = ExtractedField(field_name="state", normalized_value=st, source_type=SourceType.DERIVED)
            if name == "state" and "district" in t.fields and STATE_OF.get(t.fields["district"].normalized_value) != val:
                t.fields.pop("district")
        return changed

    def _missing(self, s: Session) -> list[str]:
        t = s.task
        if t is None:
            return []
        adapter = get_adapter(t.portal_id)
        if "district_ambiguous" in t.fields and "district" not in t.fields:
            return ["district_ambiguous"]
        return [f for f in adapter.field_order if adapter.fields[f].required and f not in t.fields]

    def _display_value(self, name: str, value: str, lang: str) -> str:
        if name == "appointment_date":
            return i18n.format_date(value, lang)
        if name == "mobile":
            return "******" + value[-4:]
        return i18n.value_label(value, lang)

    def summary_lines(self, s: Session) -> list[dict]:
        t = s.task
        adapter = get_adapter(t.portal_id)
        order = list(adapter.field_order) + (["doctor"] if "doctor" in t.fields else [])
        return [{"field": n, "label": i18n.label(n, s.language),
                 "value": self._display_value(n, t.fields[n].normalized_value, s.language),
                 "source_type": t.fields[n].source_type.value} for n in order if n in t.fields]

    # ------------------------------------------------------------ review / approval / execution
    async def review(self, sid: str) -> dict:
        s = self.get(sid)
        async with s.lock:
            if s.state != S.PREVIEWING_TASK:
                raise SessionError("There is no task summary to approve yet.")
            await self._transition(s, S.AWAITING_CONSENT)
            await events.emit(s.id, "user", "review_confirmed", "User: confirmed the review summary")
            self._say(s, "consent.ask", "consent")
            return {"session": self.snapshot(s)}

    async def approve(self, sid: str, kind: str) -> dict:
        s = self.get(sid)
        async with s.lock:
            t = s.task
            if t is None:
                raise SessionError("No task")
            if kind == "start":
                if s.state != S.AWAITING_CONSENT:
                    raise SessionError("Approval is only accepted after you have reviewed the summary.")
                await self._start_locked(s, via="button")
                return {"session": self.snapshot(s)}
            if kind == "final":
                if s.state != S.PAUSED_FOR_CONFIRMATION or not s.run:
                    raise SessionError("Nothing is waiting for final approval.")
                self._record_approval(s, "final", self._final_action_text(s))
                await events.emit(s.id, "user", "approved_final", "User: approved submission")
                await self._transition(s, S.EXECUTING)
                asyncio.create_task(self._drive(s, s.run.approve_final))
                return {"session": self.snapshot(s)}
            raise SessionError("Unknown approval kind", 400)

    async def _start_locked(self, s: Session, via: str) -> None:
        t = s.task
        values = {k: v.normalized_value for k, v in t.fields.items()}
        adapter = get_adapter(t.portal_id)
        plan = adapter.build_plan(values, t.task_id)
        t.plan = [a.model_dump(mode="json", exclude={"value"}) for a in plan]
        self._record_approval(s, "start", f"Start {adapter.name} task ({via})")
        await events.emit(s.id, "user", "approved_start", f"User: approved starting the task ({via})")
        await events.emit(s.id, "policy", "plan_approved",
                          f"Policy: plan approved — {len(plan)} actions, all within {adapter.route_prefix}", {"plan": t.plan})
        await self._transition(s, S.EXECUTING)
        self._say(s, "exec.started", "progress")
        s.run = BrowserRun(s.id, t.task_id, adapter, plan, values,
                           lambda actor, kind_, desc, data=None: events.emit(s.id, actor, kind_, desc, data))
        asyncio.create_task(self._drive(s, s.run.start))

    async def _final_wait_turn(self, s: Session, text: str, t0: float) -> dict:
        out = self.rules.interpret_sync(text, self._context(s))  # yes/no only: deterministic, no model needed
        if out.intent == Intent.CONFIRM:
            self._record_approval(s, "final", self._final_action_text(s) + " (voice)")
            await events.emit(s.id, "user", "approved_final", "User: approved submission (voice)")
            await self._transition(s, S.EXECUTING)
            asyncio.create_task(self._drive(s, s.run.approve_final))
            return self._turn_result(s, t0, intent="confirm")
        if out.intent == Intent.DENY:
            return await self._cancel_locked(s, t0)
        self._say(s, "final.ask", "approval", action=self._final_action_text(s))
        return self._turn_result(s, t0, intent=out.intent.value)

    def _final_action_text(self, s: Session) -> str:
        key = {"scheme_application": "action.submit_application", "clinic_appointment": "action.confirm_booking",
               "cancel_appointment": "action.cancel_booking"}[s.task.intent]
        return i18n.t(key, s.language)

    def _record_approval(self, s: Session, kind: str, summary: str) -> None:
        with db() as c:
            c.execute("INSERT INTO approvals (session_id, kind, summary, at) VALUES (?,?,?,?)", (s.id, kind, summary, now_iso()))

    async def _drive(self, s: Session, step) -> None:
        try:
            outcome = await step()
        except Exception as e:  # never leave a session silently stuck
            log.exception("browser run crashed")
            outcome = "failed"
            if s.run:
                s.run.state.error = f"Browser error: {type(e).__name__}"
        await self._on_outcome(s, outcome)

    async def _on_outcome(self, s: Session, outcome: str) -> None:
        async with s.lock:
            if s.state == S.CANCELLED or (s.run and s.run.state.status == "cancelled"):
                return
            run = s.run
            lang = s.language
            if outcome == "awaiting_user_input":
                if s.state != S.AWAITING_USER_ACTION:
                    await self._transition(s, S.AWAITING_USER_ACTION)
                    self._add_message(s, "assistant", i18n.t("otp.needed", lang), "user_action",
                                      {"secure_input": {"target": "otp"}})
                    await events.emit(s.id, "browser", "awaiting_user", "Browser: paused — waiting for you to enter the code")
                return
            if outcome == "paused_for_confirmation":
                await self._transition(s, S.PAUSED_FOR_CONFIRMATION)
                lines = self.summary_lines(s)
                self._add_message(s, "assistant", i18n.t("final.ask", lang, action=self._final_action_text(s)), "approval",
                                  {"summary": lines, "portal": get_adapter(s.task.portal_id).name,
                                   "consequence": "Creates a demo record on the local demo portal."})
                await events.emit(s.id, "browser", "paused_confirmation", "Browser: paused for your approval")
                return
            if outcome == "verified":
                await self._transition(s, S.VERIFYING)
                ev = run.state.evidence
                self._store_evidence(s, ev)
                await self._transition(s, S.COMPLETED)
                t = s.task
                t.result = {"reference": ev.get("reference"), "description": ev.get("description")}
                if "land_area_format" in run.state.recovered:
                    self._say(s, "exec.recovered", "progress")
                if t.intent == "scheme_application":
                    msg = self._say(s, "done.application", "success", ref=ev["reference"])
                elif t.intent == "clinic_appointment":
                    rec = ev["record"]
                    msg = self._say(s, "done.booking", "success", ref=ev["reference"], doctor=rec["doctor"],
                                    date=i18n.format_date(rec["slot_date"], lang), time=rec["slot_time"])
                else:
                    msg = self._say(s, "done.cancelled", "success", ref=ev["reference"])
                s.summary_card = {"title": get_adapter(t.portal_id).name, "reference": ev.get("reference"),
                                  "lines": self.summary_lines(s), "message": msg["text"], "language": lang,
                                  "demo_notice": "DEMO DOCUMENT — not an official record", "created_at": now_iso()}
                with db() as c:
                    c.execute("UPDATE tasks SET status='completed', data=? WHERE id=?",
                              (dumps({"reference": ev.get("reference"), "summary": s.summary_card}), t.task_id))
                await run.close()
                return
            # failed
            detail = run.state.error if run else "unknown error"
            if s.state in (S.EXECUTING, S.AWAITING_USER_ACTION, S.PAUSED_FOR_CONFIRMATION, S.VERIFYING):
                await self._transition(s, S.FAILED)
            done = [a["explanation"] for a, live in zip(s.task.plan, run.plan, strict=False) if live.status.value == "succeeded"] if run else []
            self._add_message(s, "assistant", i18n.t("fail.unverified", lang, detail=detail or ""), "error",
                              {"completed_steps": done})
            with db() as c:
                c.execute("UPDATE tasks SET status='failed' WHERE id=?", (s.task.task_id,))
            if run:
                await run.close()

    def _store_evidence(self, s: Session, ev: dict) -> None:
        with db() as c:
            c.execute("INSERT INTO evidence VALUES (?,?,?,?,?,?,?,?)",
                      (uuid.uuid4().hex[:12], s.id, s.task.task_id, "db_record", ev.get("route", ""),
                       ev.get("description", ""), "verified" if ev.get("verified") else "mismatch", now_iso()))

    async def user_input(self, sid: str, value: str) -> dict:
        s = self.get(sid)
        if s.state != S.AWAITING_USER_ACTION or not s.run:
            raise SessionError("No code is being requested right now.")
        if not re.fullmatch(r"\d{4,8}", value or ""):
            raise SessionError("The code should be 4 to 8 digits.", 400)
        await events.emit(s.id, "user", "secure_input", "User: entered the code in the secure box (not recorded)")
        async with s.lock:
            await self._transition(s, S.EXECUTING)
        asyncio.create_task(self._drive(s, lambda: s.run.provide_secret(value)))
        return {"session": self.snapshot(s)}

    async def resume(self, sid: str) -> dict:
        s = self.get(sid)
        if s.state != S.AWAITING_USER_ACTION or not s.run:
            raise SessionError("Nothing to resume.")
        async with s.lock:
            await self._transition(s, S.EXECUTING)
        asyncio.create_task(self._drive(s, s.run.resume_manual))
        return {"session": self.snapshot(s)}

    async def cancel(self, sid: str) -> dict:
        s = self.get(sid)
        async with s.lock:
            return await self._cancel_locked(s, time.perf_counter())

    async def _cancel_locked(self, s: Session, t0: float) -> dict:
        if is_terminal(s.state) or s.state == S.IDLE and not s.task:
            return self._turn_result(s, t0, intent="cancel")
        done: list[str] = []
        if s.run:
            done = await s.run.cancel()
        await self._transition(s, S.CANCELLED)
        await events.emit(s.id, "user", "cancelled", "User: cancelled the task", {"completed_steps": done})
        detail = ("Already done on the demo portal: " + "; ".join(done) + ". Nothing was submitted.") if done else "Nothing was entered on the portal."
        self._say(s, "cancelled", "info", detail=detail)
        if s.task:
            with db() as c:
                c.execute("UPDATE tasks SET status='cancelled' WHERE id=?", (s.task.task_id,))
        return self._turn_result(s, t0, intent="cancel")

    def delete(self, sid: str) -> None:
        s = SESSIONS.pop(sid, None)
        with db() as c:
            for tbl in ("events", "approvals", "browser_audit", "evidence", "task_states", "tasks"):
                c.execute(f"DELETE FROM {tbl} WHERE session_id=?", (sid,))
            c.execute("DELETE FROM sessions WHERE id=?", (sid,))
        from app.services.browser.executor import SCREENSHOT_DIR
        d = SCREENSHOT_DIR / sid
        if d.exists():
            for p in d.iterdir():
                p.unlink()
            d.rmdir()
        if s and s.run:
            asyncio.create_task(s.run.close())

    # ------------------------------------------------------------ views
    def task_intent(self, s: Session) -> TaskIntent | None:
        t = s.task
        if not t:
            return None
        adapter = get_adapter(t.portal_id)
        return TaskIntent(task_id=t.task_id, intent=Intent(t.intent), portal_id=t.portal_id, user_language=s.language,
                          required_fields=[f for f in adapter.field_order if adapter.fields[f].required],
                          known_fields=t.fields, missing_fields=self._missing(s),
                          clarification_question=next((m["text"] for m in reversed(s.messages) if m["kind"] == "question"), None)
                          if s.state == S.NEEDS_CLARIFICATION else None,
                          source_references=["pm_kisan"] if t.intent == "scheme_application" else [],
                          requires_confirmation=True, completion_criteria=adapter.completion_evidence)

    def snapshot(self, s: Session) -> dict:
        ti = self.task_intent(s)
        run = s.run
        return {
            "id": s.id, "language": s.language, "state": s.state.value, "messages": s.messages[-60:],
            "task": ti.model_dump(mode="json") if ti else None,
            "summary": self.summary_lines(s) if s.task else [],
            "expected_field": s.task.expected_field if s.task else None,
            "result": s.task.result if s.task else None,
            "summary_card": s.summary_card,
            "plan": [{**p, "status": live.status.value, "error_message": live.error_message}
                     for p, live in zip(s.task.plan, run.plan, strict=False)] if (s.task and run and s.task.plan) else [],
            "screenshots": run.state.screenshots if run else [],
            "reasoning": {"label": self.reasoner.label, "is_ai": self.reasoner.is_ai,
                          "model": self.reasoner.health.extra.get("model")},
            "last_turn": s.last_turn,
        }
