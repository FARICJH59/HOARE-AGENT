"""End-to-end control-plane validation for HOARE Case Study #1.

Provenance: 2026-09-14

This test deliberately stops at the executor seam. It proves that the
enterprise product can reach controlled admission, but physical execution is
still represented only by an injected executor callback.
"""

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    AuthorityStatus,
    ControlledActionRequest,
)
from hoare_engine.aesirgrid_case_study import (
    AegisDecision,
    AesirGridMode,
    GridTelemetry,
    SyntheticGridTelemetryProvider,
    run_aesirgrid_shadow,
)
from hoare_engine.governed_execution import execute_governed
from hoare_engine.product_factory import ProductLifecycle, build_product_definition


def test_aesirgrid_intent_to_shadow_to_controlled_admission():
    intent = (
        "Build an energy-grid predictive-maintenance system for AesirGrid "
        "using telemetry from grid assets."
    )

    product = build_product_definition(
        product_id="aesirgrid-predictive-maintenance",
        product_version="1.0.0",
        domain="energy",
        capabilities=(
            "Telemetry",
            "PredictiveMaintenance",
            "AssetHealthScoring",
            "AnomalyDetection",
        ),
        domain_policies=("energy.grid.safety.v1",),
        evidence_requirements=(
            "telemetry-integrity",
            "model-verification",
            "AEGIS-authorization",
        ),
        deployment_profiles=("simulation", "shadow", "controlled", "live"),
        vertical_ip_refs=("aesirgrid:grid-models:v1",),
        customer_ip_refs=("customer:grid-operator:telemetry:v1",),
        metadata={"intent": intent, "case_study": "HOARE-CS-001"},
    )

    for state in (
        ProductLifecycle.PLANNED,
        ProductLifecycle.BUILDING,
        ProductLifecycle.TESTING,
        ProductLifecycle.VERIFIED,
        ProductLifecycle.STAGED,
    ):
        product = product.transition(state)

    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.can_execute is False

    telemetry = SyntheticGridTelemetryProvider(
        [
            GridTelemetry(
                asset_id="substation-001",
                temperature_c=58.0,
                vibration_mm_s=2.0,
                load_pct=72.0,
                frequency_hz=60.01,
                timestamp_s=1000.0,
            ),
            GridTelemetry(
                asset_id="substation-002",
                temperature_c=104.0,
                vibration_mm_s=9.0,
                load_pct=94.0,
                frequency_hz=59.70,
                timestamp_s=1000.0,
            ),
        ]
    )

    assessments, shadow = run_aesirgrid_shadow(telemetry)

    assert len(assessments) == 2
    assert any(item.anomaly for item in assessments)
    assert shadow.decision is AegisDecision.ALLOW
    assert shadow.mode is AesirGridMode.SHADOW

    request = ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=None,
    )

    calls = []
    escalated = execute_governed(
        request,
        lambda: calls.append("executed") or "should-not-run",
    )

    assert escalated.admission.decision is AegisDecision.ESCALATE
    assert escalated.executed is False
    assert calls == []

    lease = AuthorityLease(
        lease_id="lease-aesirgrid-e2e-001",
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )
    authorized_request = ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )

    executed = execute_governed(
        authorized_request,
        lambda: calls.append("executed") or "executor-result",
    )

    assert executed.admission.decision is AegisDecision.ALLOW
    assert executed.executed is True
    assert executed.result == "executor-result"
    assert calls == ["executed"]
