"""Case-study integration tests for staged-to-authorized admission.

Provenance: 2026-09-14 13:12 EDT
"""

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    AuthorityStatus,
    ControlledActionRequest,
    admit_controlled_action,
)
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode
from hoare_engine.product_factory import ProductLifecycle, build_product_definition


def _staged_product():
    product = build_product_definition(
        product_id="aesirgrid-predictive-maintenance",
        product_version="1.0.0",
        domain="energy",
        capabilities=("Telemetry", "PredictiveMaintenance", "AssetHealthScoring", "AnomalyDetection"),
        domain_policies=("energy.grid.safety.v1",),
        evidence_requirements=("telemetry-integrity", "model-verification", "AEGIS-authorization"),
        vertical_ip_refs=("aesirgrid:grid-models:v1",),
        customer_ip_refs=("customer:grid-operator:telemetry:v1",),
    )
    for state in (
        ProductLifecycle.PLANNED,
        ProductLifecycle.BUILDING,
        ProductLifecycle.TESTING,
        ProductLifecycle.VERIFIED,
        ProductLifecycle.STAGED,
    ):
        product = product.transition(state)
    return product


def test_staged_product_requires_authority_lease_for_controlled_admission():
    product = _staged_product()

    request = ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=None,
    )

    result = admit_controlled_action(request)

    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.can_execute is False
    assert result.decision is AegisDecision.ESCALATE


def test_staged_product_can_cross_authority_boundary_only_with_matching_valid_lease():
    product = _staged_product()
    lease = AuthorityLease(
        lease_id="lease-aesirgrid-001",
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )

    result = admit_controlled_action(
        ControlledActionRequest(
            tenant_id="tenant-grid-001",
            product_id=product.product_id,
            action="apply_maintenance_setpoint",
            requested_mode=AesirGridMode.CONTROLLED,
            now_s=150.0,
            lease=lease,
        )
    )

    assert result.decision is AegisDecision.ALLOW
    assert result.lease_id == lease.lease_id
    assert product.can_execute is False


def test_live_mode_never_becomes_implicitly_allowed_by_a_controlled_lease():
    product = _staged_product()
    lease = AuthorityLease(
        lease_id="lease-aesirgrid-controlled",
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
    )

    result = admit_controlled_action(
        ControlledActionRequest(
            tenant_id="tenant-grid-001",
            product_id=product.product_id,
            action="apply_maintenance_setpoint",
            requested_mode=AesirGridMode.LIVE,
            now_s=150.0,
            lease=lease,
        )
    )

    assert result.decision is AegisDecision.DENY
    assert "mode mismatch" in result.reason
