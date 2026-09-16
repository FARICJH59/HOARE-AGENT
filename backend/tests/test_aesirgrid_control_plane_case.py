"""Integrated control-plane validation for HOARE Case Study #1.

Provenance: 2026-09-16
"""

from hoare_engine.aesirgrid_authority import AuthorityLease, ControlledActionRequest, admit_controlled_action
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode, GridTelemetry, SyntheticGridTelemetryProvider, run_aesirgrid_shadow
from hoare_engine.product_factory import ProductLifecycle, build_product_definition


def _staged_product():
    product = build_product_definition(product_id="aesirgrid-predictive-maintenance", product_version="1.0.0", domain="energy", capabilities=("Telemetry", "PredictiveMaintenance", "AssetHealthScoring", "AnomalyDetection"), domain_policies=("energy.grid.safety.v1",), evidence_requirements=("telemetry-integrity", "model-verification", "AEGIS-authorization"), vertical_ip_refs=("aesirgrid:grid-models:v1",), customer_ip_refs=("customer:grid-operator:telemetry:v1",))
    for state in (ProductLifecycle.PLANNED, ProductLifecycle.BUILDING, ProductLifecycle.TESTING, ProductLifecycle.VERIFIED, ProductLifecycle.STAGED):
        product = product.transition(state)
    return product


def test_full_case_study_shadow_to_controlled_admission():
    product = _staged_product()
    provider = SyntheticGridTelemetryProvider([GridTelemetry("substation-001", 58.0, 2.0, 72.0, 60.01, 1000.0)])
    assessments, shadow = run_aesirgrid_shadow(provider)
    assert assessments[0].anomaly is False
    assert shadow.decision is AegisDecision.ALLOW

    request = ControlledActionRequest(tenant_id="tenant-grid-001", product_id=product.product_id, action="apply_maintenance_setpoint", requested_mode=AesirGridMode.CONTROLLED, now_s=150.0, lease=None)
    assert admit_controlled_action(request).decision is AegisDecision.ESCALATE

    lease = AuthorityLease(lease_id="lease-aesirgrid-001", tenant_id="tenant-grid-001", product_id=product.product_id, action="apply_maintenance_setpoint", mode=AesirGridMode.CONTROLLED, issued_at_s=100.0, expires_at_s=200.0)
    admitted = admit_controlled_action(ControlledActionRequest(tenant_id="tenant-grid-001", product_id=product.product_id, action="apply_maintenance_setpoint", requested_mode=AesirGridMode.CONTROLLED, now_s=150.0, lease=lease))
    assert admitted.decision is AegisDecision.ALLOW
    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.can_execute is False


def test_full_case_study_cannot_cross_tenant_authority_boundary():
    product = _staged_product()
    lease = AuthorityLease(lease_id="lease-aesirgrid-other-tenant", tenant_id="tenant-grid-002", product_id=product.product_id, action="apply_maintenance_setpoint", mode=AesirGridMode.CONTROLLED, issued_at_s=100.0, expires_at_s=200.0)
    result = admit_controlled_action(ControlledActionRequest(tenant_id="tenant-grid-001", product_id=product.product_id, action="apply_maintenance_setpoint", requested_mode=AesirGridMode.CONTROLLED, now_s=150.0, lease=lease))
    assert result.decision is AegisDecision.DENY
    assert result.reason == "authority lease tenant mismatch"
