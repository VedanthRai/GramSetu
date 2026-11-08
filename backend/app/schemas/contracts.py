"""Strict data contracts (Pydantic 2). Every model output and browser action passes through these."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Sensitivity(str, Enum):
    LOW = "low"
    PERSONAL = "personal"
    SECRET = "secret"  # OTP / password / PIN: never sent to models, never logged, never spoken


class SourceType(str, Enum):
    USER_SPOKEN = "user_spoken"
    USER_CORRECTED = "user_corrected"
    SYSTEM_DEFAULT = "system_default"
    DERIVED = "derived"


class Intent(str, Enum):
    SCHEME_APPLICATION = "scheme_application"
    CLINIC_APPOINTMENT = "clinic_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    PROVIDE_INFO = "provide_info"  # answering a follow-up question
    CONFIRM = "confirm"
    DENY = "deny"
    UNSUPPORTED = "unsupported"
    EMERGENCY = "emergency"
    SECRET_SHARING_RISK = "secret_sharing_risk"


class ExtractedField(Strict):
    field_name: str = Field(min_length=1, max_length=64)
    normalized_value: str = Field(max_length=200)
    original_user_expression: str = Field(default="", max_length=300)
    source_type: SourceType = SourceType.USER_SPOKEN
    needs_confirmation: bool = False
    sensitivity_level: Sensitivity = Sensitivity.LOW


class ReasoningOutput(Strict):
    """The ONLY shape a reasoning provider may return. No code, no browser instructions."""

    intent: Intent
    fields: list[ExtractedField] = Field(default_factory=list, max_length=20)
    is_correction: bool = False
    detected_language: str | None = None
    notes: str = Field(default="", max_length=300)


class TaskIntent(Strict):
    task_id: str
    intent: Intent
    portal_id: str | None
    user_language: str
    required_fields: list[str]
    known_fields: dict[str, ExtractedField]
    missing_fields: list[str]
    clarification_question: str | None = None
    source_references: list[str] = Field(default_factory=list)
    sensitivity_level: Sensitivity = Sensitivity.PERSONAL
    requires_confirmation: bool = True
    completion_criteria: str = ""


class ActionType(str, Enum):
    NAVIGATE = "NAVIGATE"
    CLICK = "CLICK"
    FILL = "FILL"
    SELECT_OPTION = "SELECT_OPTION"
    CHECK = "CHECK"
    UNCHECK = "UNCHECK"
    SCROLL = "SCROLL"
    WAIT_FOR_ELEMENT = "WAIT_FOR_ELEMENT"
    CAPTURE_SCREENSHOT = "CAPTURE_SCREENSHOT"
    REQUEST_USER_INPUT = "REQUEST_USER_INPUT"
    PAUSE_FOR_CONFIRMATION = "PAUSE_FOR_CONFIRMATION"
    VERIFY_STATE = "VERIFY_STATE"


class ActionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class BrowserAction(Strict):
    action_id: str
    action_type: ActionType
    target: str = ""  # semantic target key from the portal adapter, or a route for NAVIGATE
    value: str | None = None
    expected_result: str = ""
    requires_authorization: bool = False
    status: ActionStatus = ActionStatus.PROPOSED
    error_message: str | None = None
    explanation: str = ""  # plain-language "why GramSetu is doing this"


class TaskEvidence(Strict):
    evidence_id: str
    evidence_type: Literal["page_state", "db_record", "screenshot", "validation_error"]
    task_id: str
    timestamp: datetime
    source_page: str
    sanitized_description: str
    verification_status: Literal["verified", "mismatch", "pending"]
