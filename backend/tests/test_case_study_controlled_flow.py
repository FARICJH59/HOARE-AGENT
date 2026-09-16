"""Integrated control-plane proof for HOARE Case Study #1.

Provenance: 2026-09-16

The test intentionally stops at authorization. It proves that the same
case-study product can progress from shadow analysis to an explicitly
authorized lifecycle state, while the product definition itself remains
non-executable.
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


PRODUCT_ID = "aesirgrid-predictive-maintenance"
TENANT_ID = "tenant-grid-001"


def _staged_product():
    product = build_product_definition(
        product_id=PRODUCT_ID,
        product_version="1.0.0",
        domain="energy",
        capabilities=("Telemetry", "PredictiveMaintenance", "AssetHealthScoring"),
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


def test_complete_case_study_shadow_to_authorized_boundary():
    provider = SyntheticGridTelemetryProvider(
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

    assessments, shadow_decision = run_aesirgrid_shadow(provider)
    product = _staged_product()

    assert len(assessments) == 2
    assert any(item.anomaly for item in assessments)
    assert shadow_decision.decision is AegisDecision.ALLOW
    assert shadow_decision.mode is AesirGridMode.SHADOW

    lease = AuthorityLease(
        lease_id="lease-aesirgrid-001",
        tenant_id=TENANT_ID,
        product_id=PRODUCT_ID,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=1000.0,
        expires_at_s=1100.0,
    )
    request = ControlledActionRequest(
        tenant_id=TENANT_ID,
        product_id=PRODUCT_ID,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=1050.0,
        lease=lease,
    )

    admission = admit_controlled_action(request)
    authorized = authorize_product(product, admission)

    assert admission.decision is AegisDecision.ALLOW
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False
    assert authorized.authority == "product-definition-only"


def test_missing_authority_stops_flow_before_authorization():
    product = _staged_product()
    admission = admit_controlled_action(
        ControlledActionRequest(
            tenant_id=TENANT_ID,
            product_id=PRODUCT_ID,
            action="apply_maintenance_setpoint",
            requested_mode=AesirGridMode.CONTROLLED,
            now_s=1050.0,
            lease=None,
        )
    )

    assert admission.decision is AegisDecision.ESCALATE

    try:
        authorize_product(product, admission)
    except ValueError as exc:
        assert "ALLOW admission" in str(exc)
    else:
        raise AssertionError("missing authority must not authorize the product")
