"""End-to-end control-plane validation for HOARE Case Study #1.

Provenance: 2026-09-16

This test deliberately stops at the executor seam. It proves that the
enterprise product can reach controlled admission and that the existing
executor callback is invoked only after explicit authority admission and
product authorization.
"""

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    AuthorityStatus,
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
from hoare_engine.governed_execution import execute_governed
from hoare_engine.product_factory import ProductLifecycle, build_product_definition


def _build_staged_product():
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
        metadata={
            "intent": "Build an energy-grid predictive-maintenance system for AesirGrid using telemetry from grid assets.",
            "case_study": "HOARE-CS-001",
        },
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


def _controlled_request(product, lease=None):
    return ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )


def _valid_lease(product):
    return AuthorityLease(
        lease_id="lease-aesirgrid-e2e-001",
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
        authority_source="human-operator-approval",
        evidence_refs=("telemetry-integrity", "model-verification"),
        scope=("apply_maintenance_setpoint",),
        audit_correlation_id="audit-aesirgrid-e2e-001",
    )


def test_aesirgrid_intent_to_shadow_to_controlled_admission():
    product = _build_staged_product()

    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.can_execute is False

    telemetry = SyntheticGridTelemetryProvider(
        [
            GridTelemetry("substation-001", 58.0, 2.0, 72.0, 60.01, 1000.0),
            GridTelemetry("substation-002", 104.0, 9.0, 94.0, 59.70, 1000.0),
        ]
    )

    assessments, shadow = run_aesirgrid_shadow(telemetry)

    assert len(assessments) == 2
    assert any(item.anomaly for item in assessments)
    assert shadow.decision is AegisDecision.ALLOW
    assert shadow.mode is AesirGridMode.SHADOW

    calls = []
    lease = _valid_lease(product)

    escalated = execute_governed(
        _controlled_request(product),
        lambda: calls.append("executed") or "should-not-run",
        product=product,
    )

    assert escalated.admission.decision is AegisDecision.ESCALATE
    assert escalated.executed is False
    assert calls == []

    admission = admit_controlled_action(_controlled_request(product, lease))
    assert admission.decision is AegisDecision.ALLOW
    assert admission.evidence_refs == ("telemetry-integrity", "model-verification")
    assert admission.audit_correlation_id == "audit-aesirgrid-e2e-001"

    staged_execution = execute_governed(
        _controlled_request(product, lease),
        lambda: calls.append("executed") or "should-not-run",
        product=product,
    )
    assert staged_execution.admission.decision is AegisDecision.DENY
    assert staged_execution.executed is False
    assert "AUTHORIZED" in staged_execution.admission.reason
    assert calls == []

    authorized_product = authorize_product(product, admission)
    assert authorized_product.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized_product.can_execute is False

    executed = execute_governed(
        _controlled_request(authorized_product, lease),
        lambda: calls.append("executed") or "executor-result",
        product=authorized_product,
    )

    assert executed.admission.decision is AegisDecision.ALLOW
    assert executed.executed is True
    assert executed.result == "executor-result"
    assert calls == ["executed"]
