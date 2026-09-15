"""End-to-end blueprint trace for HOARE Case Study #1.

Provenance: 2026-09-15

This test checks the complete control-plane sequence without pretending that
simulation, authorization, deployment, or operation are the same authority.
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
from hoare_engine.product_factory import ProductLifecycle, build_product_definition


def _staged_product():
    product = build_product_definition(
        product_id="aesirgrid-predictive-maintenance",
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


def test_aesirgrid_blueprint_end_to_end_through_authorization():
    product = _staged_product()
    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.can_execute is False

    provider = SyntheticGridTelemetryProvider(
        [
            GridTelemetry("substation-001", 58.0, 2.0, 72.0, 60.01, 1000.0),
            GridTelemetry("substation-002", 104.0, 9.0, 94.0, 59.70, 1000.0),
        ]
    )
    assessments, shadow = run_aesirgrid_shadow(provider)

    assert len(assessments) == 2
    assert shadow.decision is AegisDecision.ALLOW
    assert shadow.mode is AesirGridMode.SHADOW

    request_without_authority = ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=None,
    )
    escalated = admit_controlled_action(request_without_authority)
    assert escalated.decision is AegisDecision.ESCALATE

    lease = AuthorityLease(
        lease_id="lease-aesirgrid-001",
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
    )
    admitted = admit_controlled_action(
        ControlledActionRequest(
            tenant_id="tenant-grid-001",
            product_id=product.product_id,
            action="apply_maintenance_setpoint",
            requested_mode=AesirGridMode.CONTROLLED,
            now_s=150.0,
            lease=lease,
        )
    )
    assert admitted.decision is AegisDecision.ALLOW

    authorized = authorize_product(product, admitted)
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False

    deployed = authorized.transition(ProductLifecycle.DEPLOYED)
    assert deployed.lifecycle_state is ProductLifecycle.DEPLOYED
    assert deployed.can_execute is False

    operating = deployed.transition(ProductLifecycle.OPERATING)
    assert operating.lifecycle_state is ProductLifecycle.OPERATING
    assert operating.can_execute is False


def test_aesirgrid_blueprint_cannot_skip_authorization():
    product = _staged_product()

    try:
        product.transition(ProductLifecycle.DEPLOYED)
    except ValueError as exc:
        assert "invalid lifecycle transition" in str(exc)
    else:
        raise AssertionError("STAGED must not bypass AUTHORIZED")
