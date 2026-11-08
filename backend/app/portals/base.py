"""Portal adapter framework. The browser engine executes only what an adapter allows."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Callable, Literal

from app.schemas.contracts import ActionType, BrowserAction, Sensitivity

LocatorKind = Literal["label", "role_button", "role_link", "role_radio", "role_checkbox", "test_id", "text"]


@dataclass(frozen=True)
class Locator:
    kind: LocatorKind
    value: str  # label text / accessible name / data-testid


@dataclass(frozen=True)
class FieldSpec:
    name: str
    kind: Literal["text", "select", "number", "radio", "date", "derived"]
    required: bool = True
    options: tuple[str, ...] = ()
    sensitivity: Sensitivity = Sensitivity.LOW
    ask_key: str | None = None


@dataclass
class PortalAdapter:
    portal_id: str
    name: str
    route_prefix: str  # all routes must start with this path on the app origin
    supported_tasks: tuple[str, ...]
    fields: dict[str, FieldSpec]
    field_order: tuple[str, ...]
    targets: dict[str, Locator]  # semantic target key -> locator
    secret_targets: frozenset[str] = frozenset()  # only REQUEST_USER_INPUT may touch these
    consequential_targets: frozenset[str] = frozenset()  # require explicit approval
    permitted_actions: frozenset[ActionType] = frozenset(ActionType)
    completion_evidence: str = ""
    enabled: bool = True
    read_only: bool = False
    data_sensitivity: Sensitivity = Sensitivity.PERSONAL
    plan_builder: Callable[["PortalAdapter", dict[str, str], str], list[BrowserAction]] | None = None
    recovery: dict[str, str] = field(default_factory=dict)  # validation-error key -> recovery rule id

    def build_plan(self, values: dict[str, str], task_id: str) -> list[BrowserAction]:
        if not self.plan_builder:
            raise RuntimeError(f"{self.portal_id} has no plan builder")
        return self.plan_builder(self, values, task_id)

    def describe(self) -> dict:
        return {
            "portal_id": self.portal_id, "name": self.name, "route_prefix": self.route_prefix,
            "supported_tasks": list(self.supported_tasks), "enabled": self.enabled, "read_only": self.read_only,
            "fields": [f.name for f in self.fields.values()],
            "permitted_actions": sorted(a.value for a in self.permitted_actions),
            "consequential_targets": sorted(self.consequential_targets),
            "secret_targets": sorted(self.secret_targets),
            "completion_evidence": self.completion_evidence,
            "data_sensitivity": self.data_sensitivity.value,
        }


def act(action_type: ActionType, target: str = "", value: str | None = None, expected: str = "",
        auth: bool = False, why: str = "") -> BrowserAction:
    return BrowserAction(action_id=uuid.uuid4().hex[:10], action_type=action_type, target=target, value=value,
                         expected_result=expected, requires_authorization=auth, explanation=why)
