from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from typing import FrozenSet

# Public capabilities are deliberately explicit. Privileged capabilities are
# never included in this registry and require the internal HOARE service key.
DEFAULT_PUBLIC_CAPABILITIES: FrozenSet[str] = frozenset(
    {
        "agent.run",
        "project.analyze",
        "project.build",
        "project.verify",
        "pasor.execute",
        "aegis.verify",
        "telemetry.read",
        "deployment.request",
    }
)

PRIVATE_CAPABILITIES: FrozenSet[str] = frozenset(
    {
        "enterprise_control",
        "brain.read",
        "brain.modify",
        "policy.root",
        "control_plane.modify",
        "system.self_modify",
    }
)


@dataclass(frozen=True)
class CapabilityDecision:
    allowed: bool
    capability: str
    reason: str
    internal: bool = False


class CapabilityFirewall:
    """Server-side authorization boundary between tenants and HOARE internals."""

    def __init__(self) -> None:
        self._internal_key = os.getenv("HOARE_INTERNAL_SERVICE_KEY", "")
        configured = os.getenv("PUBLIC_CAPABILITIES", "")
        self._public = frozenset(
            item.strip() for item in configured.split(",") if item.strip()
        ) or DEFAULT_PUBLIC_CAPABILITIES

    @staticmethod
    def _matches_secret(candidate: str | None, expected: str) -> bool:
        return bool(candidate and expected) and hmac.compare_digest(candidate, expected)

    def authorize(
        self,
        capability: str,
        *,
        tenant_id: str,
        internal_service_key: str | None = None,
        entitled: bool = True,
    ) -> CapabilityDecision:
        if not capability:
            return CapabilityDecision(False, capability, "capability_required")

        if capability in PRIVATE_CAPABILITIES:
            if self._matches_secret(internal_service_key, self._internal_key):
                return CapabilityDecision(True, capability, "internal_service_authorized", True)
            return CapabilityDecision(False, capability, "private_capability_forbidden")

        if not entitled:
            return CapabilityDecision(False, capability, "capability_not_entitled")

        if capability not in self._public:
            return CapabilityDecision(False, capability, "capability_not_public")

        if not tenant_id or tenant_id == "public":
            return CapabilityDecision(False, capability, "authenticated_tenant_required")

        return CapabilityDecision(True, capability, "tenant_capability_authorized")
