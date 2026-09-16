"""Integrated AesirGrid case-study authorization tests.

Provenance: 2026-09-16
"""

import pytest

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
    assess_asset,
    evaluate_aegis,
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


def _lease(**overrides):
    values = dict(
        lease_id="lease-aesirgrid-controlled-001",
        tenant_id=TENANT_ID,
        product_id=PRODUCT_ID,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )
    values.update(overrides)
    return AuthorityLease(**values)


def _request(**overrides):
    values = dict(
        tenant_id=TENANT_ID,
        product_id=PRODUCT_ID,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=_lease(),
    )
    values.update(overrides)
    return ControlledActionRequest(**values)


def test_complete_case_study_path_reaches_shadow_then_authorized_boundary():
    provider = SyntheticGridTelemetryProvider(
        [
            GridTelemetry("substation-001", 58.0, 2.0, 72.0, 60.01, 1000.0),
            GridTelemetry("substation-002", 104.0, 9.0, 94.0, 59.70, 1000.0),
        ]
    )

    assessments, shadow = run_aesirgrid_shadow(provider)
    assert shadow.decision is AegisDecision.ALLOW
    assert shadow.mode is AesirGridMode.SHADOW
    assert any(item.anomaly for item in assessments)

    product = _staged_product()
    admission = admit_controlled_action(_request())
    authorized = authorize_product(product, admission)

    assert admission.decision is AegisDecision.ALLOW
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False


def test_low_confidence_requires_escalation_before_controlled_admission():
    assessment = assess_asset(
        GridTelemetry("substation-003", 58.0, 2.0, 72.0, 60.01, 1000.0)
    )
    uncertain = type(assessment)(
        asset_id=assessment.asset_id,
        health_score=assessment.health_score,
        anomaly=assessment.anomaly,
        confidence=0.50,
        reason=assessment.reason,
    )

    governance = evaluate_aegis(
        mode=AesirGridMode.CONTROLLED,
        assessments=(uncertain,),
        telemetry_fresh=True,
        evidence_complete=True,
    )

    assert governance.decision is AegisDecision.ESCALATE


def test_expired_authority_cannot_cross_authorization_boundary():
    admission = admit_controlled_action(_request(now_s=200.0))

    assert admission.decision is AegisDecision.DENY
    with pytest.raises(ValueError, match="ALLOW admission"):
        authorize_product(_staged_product(), admission)
