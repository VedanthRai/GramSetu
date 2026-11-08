"""Skeleton for future read-only assistance on real portals. DISABLED by default and never executes actions.

It exists to show how the registry extends; enabling it would require a per-portal security review,
an explicit origin allowlist entry, and the user's consent. GramSetu does not automate real third-party portals.
"""
from __future__ import annotations

from app.portals.base import PortalAdapter
from app.schemas.contracts import ActionType

ADAPTER = PortalAdapter(
    portal_id="live_assistance",
    name="Live portal assistance (read-only, disabled)",
    route_prefix="/__disabled__",
    supported_tasks=(),
    fields={},
    field_order=(),
    targets={},
    permitted_actions=frozenset({ActionType.CAPTURE_SCREENSHOT}),
    completion_evidence="n/a",
    enabled=False,
    read_only=True,
)
