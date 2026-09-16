"""Explicit authority/lease boundary for the AesirGrid case study.

Provenance: 2026-09-16

This module admits a controlled action only when a valid, unexpired authority
artifact is presented and AEGIS permits the requested mode. It does not issue
physical commands or replace the existing executor.
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


T = TypeVar("T")


def admit_controlled_action(
    request: ControlledActionRequest,
) -> ControlledAdmission:
    """Admit a controlled action only across the explicit authority boundary."""

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
        return ControlledAdmission(
            decision=AegisDecision.DENY,
            reason="authority lease tenant mismatch",
        )

    if lease.product_id != request.product_id:
        return ControlledAdmission(
            decision=AegisDecision.DENY,
            reason="authority lease product mismatch",
        )

    if lease.mode is not request.requested_mode:
        return ControlledAdmission(
            decision=AegisDecision.DENY,
            reason="authority lease mode mismatch",
        )

    if not lease.is_valid_at(request.now_s):
        return ControlledAdmission(
            decision=AegisDecision.DENY,
            reason="authority lease is expired or revoked",
            lease_id=lease.lease_id,
        )

    if not request.action.strip():
        return ControlledAdmission(
            decision=AegisDecision.DENY,
            reason="controlled action is required",
            lease_id=lease.lease_id,
        )

    return ControlledAdmission(
        decision=AegisDecision.ALLOW,
        reason="explicit authority lease satisfies controlled admission boundary",
        lease_id=lease.lease_id,
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
    """Delegate to the existing executor only after local admission succeeds.

    The executor is injected rather than implemented here. This preserves the
    existing execution subsystem while making the admission boundary explicit
    and testable: no executor call occurs for DENY or ESCALATE.
    """

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
