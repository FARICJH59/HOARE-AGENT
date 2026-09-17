"""Focused metadata contract tests for AesirGrid authority.

Provenance: 2026-09-16
"""

from hoare_engine.aesirgrid_authority import AuthorityLease
from hoare_engine.aesirgrid_case_study import AesirGridMode


def test_authority_lease_carries_auditable_scope_metadata():
    lease = AuthorityLease(
        lease_id="lease-001",
        tenant_id="tenant-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        authority_source="human-operator-approval",
        evidence_refs=("telemetry-integrity", "model-verification"),
        scope=("apply_maintenance_setpoint",),
        audit_correlation_id="audit-001",
    )

    assert lease.authority_source == "human-operator-approval"
    assert lease.evidence_refs == ("telemetry-integrity", "model-verification")
    assert lease.scope == ("apply_maintenance_setpoint",)
    assert lease.audit_correlation_id == "audit-001"
