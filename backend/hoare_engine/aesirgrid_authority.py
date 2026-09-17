"""Explicit authority/lease boundary for the AesirGrid case study.

Provenance: 2026-09-16

This module admits a controlled action only when a valid, unexpired authority
artifact is presented and AEGIS permits the requested mode. The lease is
bound to the exact action it authorizes and carries auditable evidence
references. It does not issue physical commands or replace the existing
executor.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, TypeVar

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
    mode: AesirGridMode
    issued_at_s: float
    expires_at_s: float
    status: AuthorityStatus = AuthorityStatus.VALID
    action: str = ""
    authority_source: str = ""
    evidence_refs: tuple[str, ...] = ()
    scope: tuple[str, ...] = ()
    audit_correlation_id: str = ""

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
    evidence_refs: tuple[str, ...] = ()
    audit_correlation_id: str | None = None


T = TypeVar("T")


def _denied(lease: AuthorityLease, reason: str) -> ControlledAdmission:
    return ControlledAdmission(
        decision=AegisDecision.DENY,
        reason=reason,
        lease_id=lease.lease_id,
        evidence_refs=lease.evidence_refs,
        audit_correlation_id=lease.audit_correlation_id or None,
    )


def admit_controlled_action(
    request: ControlledActionRequest,
) -> ControlledAdmission:
    """Admit only an explicitly leased, exactly scoped controlled/live action."""

    if request.requested_mode not in {
        AesirGridMode.CONTROLLED,
        AesirGridMode.LIVE,
    }:
        return ControlledAdmission(
            decision=AegisDecision.DENY,
            reason="controlled admission requires CONTROLLED or LIVE mode",
        )

    lease = request.lease
    if lease is None:
        return ControlledAdmission(
            decision=AegisDecision.ESCALATE,
            reason="explicit authority lease required",
        )

    if lease.tenant_id != request.tenant_id:
        return _denied(lease, "authority lease tenant mismatch")
    if lease.product_id != request.product_id:
        return _denied(lease, "authority lease product mismatch")
    if not request.action.strip():
        return _denied(lease, "controlled action is required")
    if not lease.action.strip():
        return _denied(lease, "authority lease action is required")
    if lease.action != request.action:
        return _denied(lease, "authority lease action mismatch")
    if lease.mode is not request.requested_mode:
        return _denied(lease, "authority lease mode mismatch")
    if not lease.is_valid_at(request.now_s):
        return _denied(lease, "authority lease is expired or revoked")
    if not lease.authority_source.strip():
        return _denied(lease, "authority source is required")
    if not lease.evidence_refs:
        return _denied(lease, "authority evidence is required")
    if not lease.scope:
        return _denied(lease, "authority scope is required")
    if request.action not in lease.scope:
        return _denied(lease, "authority action outside lease scope")
    if not lease.audit_correlation_id.strip():
        return _denied(lease, "audit correlation id is required")

    return ControlledAdmission(
        decision=AegisDecision.ALLOW,
        reason="explicit authority lease satisfies controlled admission boundary",
        lease_id=lease.lease_id,
        evidence_refs=lease.evidence_refs,
        audit_correlation_id=lease.audit_correlation_id,
    )


def authorize_product(
    product: ProductDefinition,
    admission: ControlledAdmission,
) -> ProductDefinition:
    """Cross STAGED -> AUTHORIZED only after a successful admission decision."""

    if product.lifecycle_state is not ProductLifecycle.STAGED:
        raise ValueError("product must be STAGED before authorization")
    if admission.decision is not AegisDecision.ALLOW:
        raise ValueError("product authorization requires an ALLOW admission")
    return product.transition(ProductLifecycle.AUTHORIZED)


def execute_authorized_action(
    request: ControlledActionRequest,
    executor: Callable[[ControlledActionRequest], T],
) -> T:
    """Delegate to the existing executor only after local admission succeeds."""

    admission = admit_controlled_action(request)
    if admission.decision is not AegisDecision.ALLOW:
        raise PermissionError(
            f"execution not admitted: {admission.decision.value}: {admission.reason}"
        )
    return executor(request)


__all__ = [
    "AuthorityLease",
    "AuthorityStatus",
    "ControlledActionRequest",
    "ControlledAdmission",
    "admit_controlled_action",
    "authorize_product",
    "execute_authorized_action",
]
