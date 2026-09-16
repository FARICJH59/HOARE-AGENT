"""Explicit authority/lease boundary for the AesirGrid case study.

Provenance: 2026-09-15
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode
from hoare_engine.product_factory import ProductDefinition, ProductLifecycle


class AuthorityStatus(str, Enum):
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


@dataclass(frozen=True)
class AuthorityLease:
    lease_id: str
    tenant_id: str
    product_id: str
    action: str
    mode: AesirGridMode
    issued_at_s: float
    expires_at_s: float
    status: AuthorityStatus = AuthorityStatus.VALID

    def is_valid_at(self, now_s: float) -> bool:
        return (
            self.status is AuthorityStatus.VALID
            and self.issued_at_s <= now_s < self.expires_at_s
        )


@dataclass(frozen=True)
class ControlledActionRequest:
    tenant_id: str
    product_id: str
    action: str
    requested_mode: AesirGridMode
    now_s: float
    lease: AuthorityLease | None


@dataclass(frozen=True)
class ControlledAdmission:
    decision: AegisDecision
    reason: str
    lease_id: str | None = None


def admit_controlled_action(request: ControlledActionRequest) -> ControlledAdmission:
    """Admit only an explicitly leased, scoped controlled/live action."""
    if request.requested_mode not in {AesirGridMode.CONTROLLED, AesirGridMode.LIVE}:
        return ControlledAdmission(AegisDecision.DENY, "controlled admission requires CONTROLLED or LIVE mode")

    lease = request.lease
    if lease is None:
        return ControlledAdmission(AegisDecision.ESCALATE, "explicit authority lease required")
    if lease.tenant_id != request.tenant_id:
        return ControlledAdmission(AegisDecision.DENY, "authority lease tenant mismatch")
    if lease.product_id != request.product_id:
        return ControlledAdmission(AegisDecision.DENY, "authority lease product mismatch")
    if lease.action != request.action:
        return ControlledAdmission(AegisDecision.DENY, "authority lease action mismatch", lease.lease_id)
    if lease.mode is not request.requested_mode:
        return ControlledAdmission(AegisDecision.DENY, "authority lease mode mismatch", lease.lease_id)
    if not lease.is_valid_at(request.now_s):
        return ControlledAdmission(AegisDecision.DENY, "authority lease is expired or revoked", lease.lease_id)
    if not request.action.strip():
        return ControlledAdmission(AegisDecision.DENY, "controlled action is required", lease.lease_id)

    return ControlledAdmission(
        AegisDecision.ALLOW,
        "explicit authority lease satisfies controlled admission boundary",
        lease.lease_id,
    )


def authorize_product(product: ProductDefinition, admission: ControlledAdmission) -> ProductDefinition:
    """Cross STAGED -> AUTHORIZED only after successful admission."""
    if product.lifecycle_state is not ProductLifecycle.STAGED:
        raise ValueError("product must be STAGED before authorization")
    if admission.decision is not AegisDecision.ALLOW:
        raise ValueError("product authorization requires an ALLOW admission")
    return product.transition(ProductLifecycle.AUTHORIZED)


__all__ = ["AuthorityLease", "AuthorityStatus", "ControlledActionRequest", "ControlledAdmission", "admit_controlled_action", "authorize_product"]