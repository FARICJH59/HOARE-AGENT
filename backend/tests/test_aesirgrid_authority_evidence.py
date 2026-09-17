"""Tests for evidence-carrying AesirGrid authority admission.

Provenance: 2026-09-16
"""

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    AuthorityStatus,
    ControlledActionRequest,
)
from hoare_engine.aesirgrid_authority_evidence import create_authority_evidence
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode


def _request(**overrides):
    lease = AuthorityLease(
        lease_id="lease-aesirgrid-evidence-001",
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )
    values = dict(
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )
    values.update(overrides)
    return ControlledActionRequest(**values)


def test_valid_allow_emits_bounded_authority_evidence():
    admission, artifact = create_authority_evidence(
        _request(),
        evidence_id="evidence-001",
        audit_correlation_id="audit-001",
        evidence_refs=("telemetry-integrity", "model-verification"),
    )

    assert admission.decision is AegisDecision.ALLOW
    assert artifact is not None
    assert artifact.evidence_id == "evidence-001"
    assert artifact.lease_id == "lease-aesirgrid-evidence-001"
    assert artifact.tenant_id == "tenant-grid-001"
    assert artifact.product_id == "aesirgrid-predictive-maintenance"
    assert artifact.action == "apply_maintenance_setpoint"
    assert artifact.mode == "CONTROLLED"
    assert artifact.decision == "ALLOW"
    assert artifact.evidence_refs == ("telemetry-integrity", "model-verification")
    assert artifact.audit_correlation_id == "audit-001"


def test_denied_or_escalated_request_emits_no_authority_evidence():
    admission, artifact = create_authority_evidence(
        _request(lease=None),
        evidence_id="evidence-denied",
        audit_correlation_id="audit-denied",
        evidence_refs=("telemetry-integrity",),
    )

    assert admission.decision is AegisDecision.ESCALATE
    assert artifact is None


def test_expired_lease_emits_no_authority_evidence():
    request = _request(now_s=200.0)

    admission, artifact = create_authority_evidence(
        request,
        evidence_id="evidence-expired",
        audit_correlation_id="audit-expired",
        evidence_refs=("telemetry-integrity",),
    )

    assert admission.decision is AegisDecision.DENY
    assert artifact is None
