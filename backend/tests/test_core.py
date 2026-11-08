"""Unit tests: state machine, contracts, policy, guards, sanitising, audio, reasoning validation."""
from __future__ import annotations

import asyncio
import json
import struct

import pytest
from app.core.logging import sanitize
from app.portals.demo_clinic import ADAPTER as CLINIC
from app.portals.demo_scheme import ADAPTER as SCHEME
from app.portals.live_assistance import ADAPTER as LIVE
from app.schemas.contracts import ActionType, BrowserAction, ReasoningOutput
from app.security import guards
from app.services.browser import policy
from app.services.reasoning.base import DialogueContext, ReasoningFailure
from app.services.reasoning.llm import _LLMBase, build_user_message
from app.services.reasoning.rules import RulesReasoner
from app.services.speech.wav import AudioError, build_wav, normalise_wav, parse_wav, validate_for_stt
from app.services.state_machine import TRANSITIONS, IllegalTransition, State, check_transition
from pydantic import ValidationError


# ------------------------------------------------------------------ state machine
def test_legal_and_illegal_transitions():
    assert check_transition(State.IDLE, State.INTERPRETING) == State.INTERPRETING
    with pytest.raises(IllegalTransition):
        check_transition(State.IDLE, State.EXECUTING)  # cannot execute without review + consent
    with pytest.raises(IllegalTransition):
        check_transition(State.PREVIEWING_TASK, State.EXECUTING)
    with pytest.raises(IllegalTransition):
        check_transition(State.COMPLETED, State.EXECUTING)


def test_cancel_allowed_from_every_non_terminal_state():
    for s in State:
        if s in (State.COMPLETED, State.FAILED, State.CANCELLED):
            assert State.CANCELLED not in TRANSITIONS[s]
        else:
            assert check_transition(s, State.CANCELLED) == State.CANCELLED


def test_executing_only_reachable_from_consent_or_pauses():
    sources = {s for s, targets in TRANSITIONS.items() if State.EXECUTING in targets}
    assert sources == {State.AWAITING_CONSENT, State.AWAITING_USER_ACTION, State.PAUSED_FOR_CONFIRMATION, State.VERIFYING}


# ------------------------------------------------------------------ contracts
def test_unknown_action_type_rejected():
    with pytest.raises(ValidationError):
        BrowserAction(action_id="x", action_type="EXECUTE_JS", target="document")
    with pytest.raises(ValidationError):
        BrowserAction(action_id="x", action_type=ActionType.CLICK, target="a", extra_field="nope")


def test_malformed_reasoning_output_rejected():
    for bad in ['{"intent": "hack_the_planet"}', '{"intent": "clinic_appointment", "fields": "x"}',
                '{"intent": "clinic_appointment", "shell": "rm -rf /"}', "not json"]:
        with pytest.raises(ValidationError):
            ReasoningOutput.model_validate_json(bad)


class FakeLLM(_LLMBase):
    label = "fake"

    def __init__(self, replies):
        super().__init__("fake", "fake-model", True)
        self.replies, self.prompts = list(replies), []

    async def _call(self, user_msg, feedback):
        self.prompts.append((user_msg, feedback))
        return self.replies.pop(0)


CTX = DialogueContext(language="hi-IN", today_iso="2026-11-08", weekday="Sunday")


def test_llm_retries_once_with_validation_error_then_succeeds():
    llm = FakeLLM(['{"intent": "bogus"}', '{"intent": "clinic_appointment", "fields": []}'])
    out = asyncio.run(llm.interpret("doctor chahiye", CTX))
    assert out.intent.value == "clinic_appointment"
    assert llm.prompts[1][1] is not None  # second call carried the validation error


def test_llm_fails_after_two_malformed_outputs():
    llm = FakeLLM(['{"intent": "bogus"}', "garbage"])
    with pytest.raises(ReasoningFailure):
        asyncio.run(llm.interpret("x", CTX))


def test_model_prompt_has_minimum_data():
    msg = build_user_message("मेरा मोबाइल 9876543210 है, आधार 1234 5678 9012", CTX)
    assert "9876543210" not in msg and "1234 5678 9012" not in msg
    assert "[NUMBER_REDACTED]" in msg


# ------------------------------------------------------------------ policy
def act(t, target="", value=None, auth=False):
    return BrowserAction(action_id="t", action_type=t, target=target, value=value, requires_authorization=auth)


def test_navigation_to_unapproved_origin_rejected():
    for target in ("https://evil.example/collect", "//evil.example/x", "/portal/clinic/../../api/usage", "/api/usage", "javascript:alert(1)"):
        with pytest.raises(policy.PolicyViolation):
            policy.validate(act(ActionType.NAVIGATE, target), SCHEME, approved_final=False, current_url=None)


def test_actions_on_foreign_page_rejected():
    with pytest.raises(policy.PolicyViolation):
        policy.validate(act(ActionType.FILL, "full_name", "x"), SCHEME, approved_final=False, current_url="https://evil.example/")


def test_otp_field_only_for_user():
    with pytest.raises(policy.PolicyViolation):
        policy.validate(act(ActionType.FILL, "otp", "123456"), SCHEME, approved_final=True, current_url=None)
    policy.validate(act(ActionType.REQUEST_USER_INPUT, "otp"), SCHEME, approved_final=False, current_url=None)


def test_consequential_action_needs_approval():
    with pytest.raises(policy.PolicyViolation):
        policy.validate(act(ActionType.CLICK, "submit_application", auth=True), SCHEME, approved_final=False, current_url=None)
    with pytest.raises(policy.PolicyViolation):  # missing authorization flag, even with approval
        policy.validate(act(ActionType.CLICK, "confirm_booking", auth=False), CLINIC, approved_final=True, current_url=None)
    policy.validate(act(ActionType.CLICK, "confirm_booking", auth=True), CLINIC, approved_final=True, current_url=None)


def test_model_proposed_unknown_target_rejected():
    with pytest.raises(policy.PolicyViolation):
        policy.validate(act(ActionType.CLICK, "#delete-everything"), CLINIC, approved_final=True, current_url=None)


def test_disabled_live_adapter_cannot_act():
    with pytest.raises(policy.PolicyViolation):
        policy.validate(act(ActionType.CLICK, "anything"), LIVE, approved_final=True, current_url=None)


def test_plans_contain_only_allowed_actions_and_gates():
    vals = {"full_name": "A", "state": "karnataka", "district": "mysuru", "village": "V", "land_area_acres": "2",
            "ownership": "owner", "bank_account_linked": "yes", "mobile": "9876543210"}
    plan = SCHEME.build_plan(vals, "t1")
    kinds = [a.action_type for a in plan]
    assert ActionType.REQUEST_USER_INPUT in kinds and ActionType.PAUSE_FOR_CONFIRMATION in kinds
    assert kinds.index(ActionType.PAUSE_FOR_CONFIRMATION) < kinds.index(ActionType.VERIFY_STATE)
    pause = kinds.index(ActionType.PAUSE_FOR_CONFIRMATION)
    for a in plan:
        if a.target in SCHEME.consequential_targets and a.action_type not in (ActionType.PAUSE_FOR_CONFIRMATION,):
            assert a.requires_authorization and plan.index(a) > pause
    assert all("otp" != a.target or a.action_type == ActionType.REQUEST_USER_INPUT for a in plan)


# ------------------------------------------------------------------ guards
@pytest.mark.parametrize("text", [
    "my OTP is 4 8 2 1 9 3", "मेरा ओटीपी 482193 है", "ಒಟಿಪಿ 482193", "என் ஓடிபி 482193",
    "a man from the bank called and asked for my OTP", "बैंक वाले ने फोन पर ओटीपी माँगा, बता दूँ?",
    "share my upi pin", "my account number is", ])
def test_secret_and_scam_detected(text):
    assert guards.is_secret_or_scam(text)


@pytest.mark.parametrize("text", ["मैं किसान हूँ", "ನನಗೆ ನಾಳೆ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬೇಕು", "my mobile is 9876543210", "10:30 please"])
def test_normal_speech_not_flagged(text):
    assert not guards.is_secret_or_scam(text)


@pytest.mark.parametrize("text", ["I have chest pain", "मुझे सीने में दर्द है", "ಎದೆ ನೋವು ಇದೆ", "நெஞ்சு வலி", "he is unconscious"])
def test_emergency_detected(text):
    assert guards.is_emergency(text)


def test_mobile_extracted_locally():
    assert guards.extract_mobile("मेरा नंबर 98765 43210 है") == "9876543210"
    assert guards.extract_mobile("+91 98765-43210") == "9876543210"
    assert guards.extract_mobile("2 एकड़") is None


def test_logs_are_sanitised():
    s = sanitize("key vach_ABCDEFGHIJKLMNOP otp 482193 aadhaar 1234 5678 9012 phone 9876543210")
    assert "vach_" not in s and "482193" not in s and "9012" not in s and "9876543210" not in s


# ------------------------------------------------------------------ audio
def tone(seconds: float, amp: int = 8000) -> bytes:
    n = int(16000 * seconds)
    return build_wav(struct.pack(f"<{n}h", *[(amp if (i // 20) % 2 else -amp) for i in range(n)]), 16000)


def test_wav_validation_paths():
    info = validate_for_stt(tone(1.0))
    assert abs(info.duration_s - 1.0) < 0.01
    with pytest.raises(AudioError, match="too short"):
        validate_for_stt(tone(0.1))
    with pytest.raises(AudioError):
        validate_for_stt(tone(31))
    with pytest.raises(AudioError) as e:
        validate_for_stt(tone(1.0, amp=0))
    assert e.value.code == "SILENCE"
    with pytest.raises(AudioError):
        validate_for_stt(b"OggS" + b"\x00" * 100)


def test_streaming_placeholder_header_is_normalised():
    w = bytearray(tone(0.5))
    w[40:44] = struct.pack("<I", 0xFFFFFFFF)  # what Timbre returns
    assert parse_wav(bytes(w)).duration_s == pytest.approx(0.5, abs=0.01)
    fixed = normalise_wav(bytes(w))
    assert struct.unpack("<I", fixed[40:44])[0] == len(fixed) - 44


# ------------------------------------------------------------------ rules reasoning
R = RulesReasoner()


def ctx(lang, **kw):
    return DialogueContext(language=lang, today_iso="2026-11-08", weekday="Sunday", **kw)


def test_rules_hindi_scheme_sample():
    out = R.interpret_sync("मैं किसान हूँ। मेरे पास दो एकड़ जमीन है। मुझे बताइए कि इस योजना के लिए क्या जानकारी चाहिए और डेमो फॉर्म भरने में मदद कीजिए।", ctx("hi-IN"))
    assert out.intent.value == "scheme_application"
    assert {f.field_name: f.normalized_value for f in out.fields}["land_area_acres"] == "2"


def test_rules_bank_yes_not_flipped_by_other_clauses():
    # Regression: the "ना " in "भरना है" (a later clause) used to be read as "no" for the bank account.
    out = R.interpret_sync("मैं किसान हूँ, मेरा नाम रमेश कुमार है, मेरे पास 2 एकड़ ज़मीन है, बैंक खाता भी है, "
                           "मुझे पीएम किसान का डेमो फॉर्म भरना है।", ctx("hi-IN"))
    assert {f.field_name: f.normalized_value for f in out.fields}["bank_account_linked"] == "yes"
    out = R.interpret_sync("मैं किसान हूँ, मेरा बैंक खाता नहीं है, मुझे डेमो फॉर्म भरना है", ctx("hi-IN"))
    assert {f.field_name: f.normalized_value for f in out.fields}["bank_account_linked"] == "no"


def test_rules_kannada_clinic_sample():
    out = R.interpret_sync("ನನಗೆ ನಾಳೆ ಬೆಳಿಗ್ಗೆ ವೈದ್ಯರ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬೇಕು. ಕನ್ನಡದಲ್ಲಿ ಸಹಾಯ ಮಾಡಿ.", ctx("kn-IN"))
    f = {x.field_name: x.normalized_value for x in out.fields}
    assert out.intent.value == "clinic_appointment" and f["appointment_date"] == "2026-11-09" and f["time_preference"] == "morning"


def test_rules_spoken_correction():
    out = R.interpret_sync("no, make it Friday", ctx("en-IN", current_intent="clinic_appointment", known_field_names=["appointment_date"]))
    assert out.is_correction and {f.field_name: f.normalized_value for f in out.fields}["appointment_date"] == "2026-11-13"


def test_rules_ambiguous_district_not_guessed():
    out = R.interpret_sync("बेंगलुरु", ctx("hi-IN", current_intent="scheme_application", expected_field="state"))
    assert [f.field_name for f in out.fields] == ["district_ambiguous"]


def test_capabilities_file_is_consistent():
    from app.services.speech.base import CAPABILITIES_FILE
    caps = json.loads(CAPABILITIES_FILE.read_text(encoding="utf-8"))
    for code, c in caps["languages"].items():
        if c["stt"] == "verified":
            assert c["voices_verified"], f"{code} verified without a verified voice"


def test_rules_colloquial_kannada_ownership():
    out = R.interpret_sync("ನಾನು ರೈತ, ಎರಡು ಎಕರೆ ಜಮೀನು ಇದೆ, ನನ್ನ ಹೆಸರಲ್ಲೇ. ಪಿಎಂ ಕಿಸಾನ್ ಡೆಮೊ ಫಾರ್ಮ್ ತುಂಬೋಕೆ ಸಹಾಯ ಮಾಡಿ.", ctx("kn-IN"))
    assert {f.field_name: f.normalized_value for f in out.fields}["ownership"] == "owner"


def test_rules_inline_name_without_punctuation():
    # Real Prisma output for the demo sentence has no punctuation; the name must not swallow the rest of the sentence.
    t = ("ನಮಸ್ಕಾರ ನಾನು ರೈತ ನನ್ನ ಹೆಸರು ರಮೇಶ್ ಕುಮಾರ್ ಬೆಂಗಳೂರು ಕಡೆ ಊರು ಹಾರೋಹಳ್ಳಿ ಎರಡು ಎಕರೆ ಜಮೀನು ಇದೆ ನನ್ನ ಹೆಸರಲ್ಲೇ "
         "ಬ್ಯಾಂಕ್ ಖಾತೆಯೂ ಇದೆ ಪಿ ಎಂ ಕಿಸಾನ್ ಡೆಮೋ ಫಾರ್ಮ್ ತುಂಬೋಕ್ಕೆ ಸಹಾಯ ಮಾಡಿ")
    f = {x.field_name: x.normalized_value for x in R.interpret_sync(t, ctx("kn-IN")).fields}
    assert f["full_name"] == "ರಮೇಶ್ ಕುಮಾರ್" and f["village"] == "ಹಾರೋಹಳ್ಳಿ" and f["bank_account_linked"] == "yes"
    f = {x.field_name: x.normalized_value for x in R.interpret_sync(
        "मैं किसान हूँ मेरा नाम रमेश कुमार है मैं बेंगलुरु से हूँ गाँव हरोहल्ली", ctx("hi-IN")).fields}
    assert f["full_name"] == "रमेश कुमार"
