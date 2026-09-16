"""Case-study authorization chain integration tests.

Provenance: 2026-09-16

These tests stop at AUTHORIZED. They do not invoke a physical controller or
replace the existing executor.
"""

import pytest

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
        capabilities=("Telemetry", "PredictiveMaintenance"),
        domain_policies=("energy.grid.safety.v1",),
        evidence_requirements=("telemetry-integrity", "model-verification", "AEGIS-authorization"),
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


def _nominal_provider():
    return SyntheticGridTelemetryProvider(
        [
            GridTelemetry(
                asset_id="substation-001",
                temperature_c=58.0,
                vibration_mm_s=2.0,
                load_pct=72.0,
                frequency_hz=60.01,
                timestamp_s=1000.0,
            )
        ]
    )


def _lease():
    return AuthorityLease(
        lease_id="lease-aesirgrid-001",
        tenant_id=TENANT_ID,
        product_id=PRODUCT_ID,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
    )


def test_case_study_shadow_to_authorized_chain():
    assessments, shadow = run_aesirgrid_shadow(_nominal_provider())
    assert assessments
    assert shadow.decision is AegisDecision.ALLOW
    assert shadow.mode is AesirGridMode.SHADOW

    admission = admit_controlled_action(
        ControlledActionRequest(
            tenant_id=TENANT_ID,
            product_id=PRODUCT_ID,
            action="apply_maintenance_setpoint",
            requested_mode=AesirGridMode.CONTROLLED,
            now_s=150.0,
            lease=_lease(),
        )
    )
    assert admission.decision is AegisDecision.ALLOW

    authorized = authorize_product(_staged_product(), admission)
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False


def test_case_study_missing_authority_stops_before_authorization():
    admission = admit_controlled_action(
        ControlledActionRequest(
            tenant_id=TENANT_ID,
            product_id=PRODUCT_ID,
            action="apply_maintenance_setpoint",
            requested_mode=AesirGridMode.CONTROLLED,
            now_s=150.0,
            lease=None,
        )
    )

    assert admission.decision is AegisDecision.ESCALATE
    with pytest.raises(ValueError, match="ALLOW admission"):
        authorize_product(_staged_product(), admission)


def test_case_study_tenant_boundary_blocks_cross_tenant_authority():
    admission = admit_controlled_action(
        ControlledActionRequest(
            tenant_id="tenant-attacker",
            product_id=PRODUCT_ID,
            action="apply_maintenance_setpoint",
            requested_mode=AesirGridMode.CONTROLLED,
            now_s=150.0,
            lease=_lease(),
        )
    )

    assert admission.decision is AegisDecision.DENY
    assert "tenant mismatch" in admission.reason
