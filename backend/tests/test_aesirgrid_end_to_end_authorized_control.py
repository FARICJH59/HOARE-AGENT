"""Full control-plane case study for AesirGrid.

Provenance: 2026-09-16

This test connects the already-implemented product factory, synthetic shadow
analysis, authority lease, product authorization, and executor-neutral seam.
It uses a recording fake executor so no physical or provider operation occurs.
"""

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    ControlledActionRequest,
    admit_controlled_action,
    authorize_product,
)
from hoare_engine.aesirgrid_case_study import (
    AegisDecision,
    AesirGridMode,
    GridTelemetry,
    SyntheticGridTelemetryProvider,
    run_aesirgrid_shadow,
)
from hoare_engine.aesirgrid_control_boundary import execute_governed_control
from hoare_engine.product_factory import ProductLifecycle, build_product_definition

PRODUCT_ID = "aesirgrid-predictive-maintenance"
TENANT_ID = "tenant-grid-001"


def _staged_product():
    product = build_product_definition(
        product_id=PRODUCT_ID,
        product_version="1.0.0",
        domain="energy",
        capabilities=("Telemetry", "PredictiveMaintenance", "AssetHealthScoring", "AnomalyDetection"),
        domain_policies=("energy.grid.safety.v1",),
        workflows=("telemetry-ingestion", "asset-health-assessment"),
        integrations=("grid-telemetry",),
        deployment_profiles=("simulation", "shadow", "controlled", "live"),
        compliance_profiles=("NIST-AI-RMF",),
        evidence_requirements=("telemetry-integrity", "model-verification", "AEGIS-authorization"),
        vertical_ip_refs=("aesirgrid:grid-models:v1",),
        customer_ip_refs=("customer:grid-operator:telemetry:v1",),
        metadata={"case_study": "HOARE-CS-001"},
    )
    for state in (ProductLifecycle.PLANNED, ProductLifecycle.BUILDING, ProductLifecycle.TESTING, ProductLifecycle.VERIFIED, ProductLifecycle.STAGED):
        product = product.transition(state)
    return product


def _lease():
    return AuthorityLease(
        lease_id="lease-aesirgrid-e2e-001",
        tenant_id=TENANT_ID,
        product_id=PRODUCT_ID,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
    )


def _request(lease=None):
    return ControlledActionRequest(
        tenant_id=TENANT_ID,
        product_id=PRODUCT_ID,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )


def test_complete_case_study_reaches_authorized_existing_executor():
    product = _staged_product()
    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.can_execute is False

    provider = SyntheticGridTelemetryProvider([
        GridTelemetry(
            asset_id="substation-001",
            temperature_c=58.0,
            vibration_mm_s=2.0,
            load_pct=72.0,
            frequency_hz=60.01,
            timestamp_s=1000.0,
        )
    ])
    assessments, shadow = run_aesirgrid_shadow(provider)
    assert len(assessments) == 1
    assert shadow.decision is AegisDecision.ALLOW
    assert shadow.mode is AesirGridMode.SHADOW

    calls = []
    denied = execute_governed_control(_request(None), lambda: calls.append("physical-operation"))
    assert denied.admission.decision is AegisDecision.ESCALATE
    assert denied.executed is False
    assert calls == []

    request = _request(_lease())
    admission = admit_controlled_action(request)
    assert admission.decision is AegisDecision.ALLOW
    assert admission.lease_id == "lease-aesirgrid-e2e-001"

    authorized = authorize_product(product, admission)
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False

    calls = []
    result = execute_governed_control(
        request,
        lambda: calls.append("physical-operation") or "executor-ok",
    )
    assert result.admission.decision is AegisDecision.ALLOW
    assert result.executed is True
    assert result.executor_result == "executor-ok"
    assert calls == ["physical-operation"]


def test_case_study_rejects_tenant_mismatch_before_executor():
    calls = []
    base = _request(_lease())
    request = ControlledActionRequest(
        tenant_id="different-tenant",
        product_id=base.product_id,
        action=base.action,
        requested_mode=base.requested_mode,
        now_s=base.now_s,
        lease=base.lease,
    )
    result = execute_governed_control(request, lambda: calls.append("executed"))
    assert result.admission.decision is AegisDecision.DENY
    assert result.executed is False
    assert calls == []
