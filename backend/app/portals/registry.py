from __future__ import annotations

from app.portals import demo_clinic, demo_scheme, live_assistance
from app.portals.base import PortalAdapter

REGISTRY: dict[str, PortalAdapter] = {
    a.portal_id: a for a in (demo_scheme.ADAPTER, demo_clinic.ADAPTER, demo_clinic.CANCEL_ADAPTER, live_assistance.ADAPTER)
}
TASK_TO_PORTAL = {"scheme_application": "demo_scheme", "clinic_appointment": "demo_clinic",
                  "cancel_appointment": "demo_clinic_cancel"}


def get_adapter(portal_id: str) -> PortalAdapter:
    a = REGISTRY.get(portal_id)
    if a is None or not a.enabled:
        raise PermissionError(f"Portal {portal_id} is not registered or is disabled")
    return a
