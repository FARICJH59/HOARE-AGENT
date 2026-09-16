"""Cross-layer AesirGrid case-study admission tests.

Provenance: 2026-09-16

These tests bind the existing product-factory lifecycle to the synthetic
shadow workflow and then exercise the explicit authority boundary. They do
not invoke a physical controller or replace the existing executor.
"""

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    AuthorityStatus,
    ControlledActionRequest,
    admit_controlled_action,
)
from hoare_engine.aesirgrid_case_study import (
    AegisDecision,
    AesirGridMode,
    GridTelemetry,
    SyntheticGridTelemetryProvider,
    run_aesirgrid_shadow,
)
from hoare_engine.product_factory import ProductLifecycle, build_product_definition


PRODUCT_ID = "aesirgrid-predictive-maintenance"
TENANT_ID = "tenant-grid-001"


def _product():
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
    for target in (
        ProductLifecycle.PLANNED,
        ProductLifecycle.BUILDING,
        ProductLifecycle.TESTING,
        ProductLifecycle.VERIFIED,
        ProductLifecycle.STAGED,
    ):
        product = product.transition(target)
    return product


def _shadow():
    provider = SyntheticGridTelemetryProvider(
        [
            GridTelemetry("substation-001", 58.0, 2.0, 72.0, 60.01, 1000.0),
            GridTelemetry("substation-002", 104.0, 9.0, 94.0, 59.70, 1000.0),
        ]
    )
    return run_aesirgrid_shadow(provider)


def test_full_case_study_reaches_shadow_before_controlled_authority():
    product = _product()
    assessments, shadow_decision = _shadow()

    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.can_execute is False
    assert len(assessments) == 2
    assert shadow_decision.decision is AegisDecision.ALLOW
    assert shadow_decision.mode is AesirGridMode.SHADOW

    no_lease = admit_controlled_action(
        ControlledActionRequest(
            tenant_id=TENANT_ID,
            product_id=PRODUCT_ID,
            action="apply_maintenance_setpoint",
            requested_mode=AesirGridMode.CONTROLLED,
            now_s=150.0,
            lease=None,
        )
    )
    assert no_lease.decision is AegisDecision.ESCALATE


def test_full_case_study_allows_controlled_admission_only_with_bound_lease():
    product = _product()
    assert product.lifecycle_state is ProductLifecycle.STAGED

    lease = AuthorityLease(
        lease_id="lease-aesirgrid-001",
        tenant_id=TENANT_ID,
        product_id=PRODUCT_ID,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )

    admitted = admit_controlled_action(
        ControlledActionRequest(
            tenant_id=TENANT_ID,
            product_id=PRODUCT_ID,
            action="apply_maintenance_setpoint",
            requested_mode=AesirGridMode.CONTROLLED,
            now_s=150.0,
            lease=lease,
        )
    )

    assert admitted.decision is AegisDecision.ALLOW
    assert admitted.lease_id == lease.lease_id


def test_full_case_study_expired_authority_cannot_admit_controlled_action():
    lease = AuthorityLease(
        lease_id="lease-aesirgrid-expired",
        tenant_id=TENANT_ID,
        product_id=PRODUCT_ID,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )

    result = admit_controlled_action(
        ControlledActionRequest(
            tenant_id=TENANT_ID,
            product_id=PRODUCT_ID,
            action="apply_maintenance_setpoint",
            requested_mode=AesirGridMode.CONTROLLED,
            now_s=200.0,
            lease=lease,
        )
    )

    assert result.decision is AegisDecision.DENY
