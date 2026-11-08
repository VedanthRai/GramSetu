"""Action-policy validator. Every BrowserAction passes here before execution; anything else is rejected."""
from __future__ import annotations

from urllib.parse import urljoin, urlparse

from app.core.config import get_settings
from app.portals.base import PortalAdapter
from app.schemas.contracts import ActionType, BrowserAction

MAX_VALUE_LEN = 200


class PolicyViolation(PermissionError):
    pass


def allowed_origin() -> str:
    u = urlparse(get_settings().app_origin)
    return f"{u.scheme}://{u.netloc}"


def is_allowed_url(url: str, adapter: PortalAdapter) -> bool:
    u = urlparse(url)
    if f"{u.scheme}://{u.netloc}" != allowed_origin():
        return False
    return u.path.startswith(adapter.route_prefix) and ".." not in u.path


def resolve_navigation(target: str, adapter: PortalAdapter) -> str:
    if "://" in target or target.startswith("//") or not target.startswith("/"):
        raise PolicyViolation("Navigation targets must be adapter routes, never external URLs")
    url = urljoin(allowed_origin(), target)
    if not is_allowed_url(url, adapter):
        raise PolicyViolation(f"Route {target} is outside the approved portal routes")
    return url


def validate(action: BrowserAction, adapter: PortalAdapter, *, approved_final: bool, current_url: str | None) -> None:
    if not adapter.enabled or adapter.read_only and action.action_type != ActionType.CAPTURE_SCREENSHOT:
        raise PolicyViolation(f"Portal {adapter.portal_id} does not permit actions")
    if not isinstance(action.action_type, ActionType):
        raise PolicyViolation("Unknown action type")
    if action.action_type not in adapter.permitted_actions:
        raise PolicyViolation(f"{action.action_type.value} is not permitted on {adapter.portal_id}")
    if action.value is not None and len(action.value) > MAX_VALUE_LEN:
        raise PolicyViolation("Action value too long")
    if action.action_type == ActionType.NAVIGATE:
        resolve_navigation(action.target, adapter)
        return
    if current_url is not None and current_url != "about:blank" and not is_allowed_url(current_url, adapter):
        raise PolicyViolation("The browser is on a page outside the approved portal; stopping")
    if action.action_type in (ActionType.CAPTURE_SCREENSHOT, ActionType.SCROLL):
        return
    if action.target not in adapter.targets:
        raise PolicyViolation(f"Target {action.target!r} is not defined by the {adapter.portal_id} adapter")
    if action.target in adapter.secret_targets and action.action_type != ActionType.REQUEST_USER_INPUT:
        raise PolicyViolation("Secret fields (OTP) may only be completed by the user")
    if action.target in adapter.consequential_targets and action.action_type not in (
            ActionType.PAUSE_FOR_CONFIRMATION, ActionType.VERIFY_STATE):
        if not action.requires_authorization:
            raise PolicyViolation("Consequential action is missing its authorization requirement")
        if not approved_final:
            raise PolicyViolation("Consequential action attempted without the user's explicit approval")
