"""Evidence-carrying authority artifact for the AesirGrid case study.

Provenance: 2026-09-16

The artifact records the bounded authority decision and evidence references.
It is evidence of admission, not an unrestricted execution credential.
"""

from __future__ import annotations

from dataclasses import dataclass

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    ControlledActionRequest,
    ControlledAdmission,
    admit_controlled_action,
)
from hoare_engine.aesirgrid_case_study import AegisDecision


@dataclass(frozen=True)
class AuthorityEvidence:
    evidence_id: str
    lease_id: str
    tenant_id: str
    product_id: str
    action: str
    mode: str
    issued_at_s: float
    expires_at_s: float
    decision: str
    evidence_refs: tuple[str, ...]
    audit_correlation_id: str


def create_authority_evidence(
    request: ControlledActionRequest,
    *,
    evidence_id: str,
    audit_correlation_id: str,
    evidence_refs: tuple[str, ...],
) -> tuple[ControlledAdmission, AuthorityEvidence | None]:
    """Evaluate a request and emit evidence only for an ALLOW decision."""

    admission = admit_controlled_action(request)
    lease = request.lease
    if admission.decision is not AegisDecision.ALLOW or lease is None:
        return admission, None

    artifact = AuthorityEvidence(
        evidence_id=evidence_id,
        lease_id=lease.lease_id,
        tenant_id=request.tenant_id,
        product_id=request.product_id,
        action=request.action,
        mode=request.requested_mode.value,
        issued_at_s=lease.issued_at_s,
        expires_at_s=lease.expires_at_s,
        decision=admission.decision.value,
        evidence_refs=tuple(evidence_refs),
        audit_correlation_id=audit_correlation_id,
    )
    return admission, artifact


__all__ = ["AuthorityEvidence", "create_authority_evidence"]
