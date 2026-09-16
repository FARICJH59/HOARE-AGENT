"""End-to-end AesirGrid authorization boundary tests.

Provenance: 2026-09-16
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
from hoare_engine.product_factory import ProductLifecycle, build_product_definition


def _product():
    product = build_product_definition(
        product_id="aesirgrid-predictive-maintenance",
        product_version="1.0.0",
        domain="energy",
        capabilities=("Telemetry", "PredictiveMaintenance"),
        domain_policies=("energy.grid.safety.v1",),
        evidence_requirements=("telemetry-integrity", "model-verification", "AEGIS-authorization"),
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


def _lease(product, *, expires_at_s=200.0, status=AuthorityStatus.VALID):
    return AuthorityLease(
        lease_id="lease-aesirgrid-integration-001",
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=expires_at_s,
        status=status,
    )


def test_case_study_shadow_result_does_not_authorize_control_by_itself():
    provider = SyntheticGridTelemetryProvider(
        [
            GridTelemetry("asset-001", 104.0, 9.0, 94.0, 59.70, 1000.0),
        ]
    )
    _, decision = run_aesirgrid_shadow(provider)

    assert decision.decision is AegisDecision.ALLOW
    assert decision.mode is AesirGridMode.SHADOW

    product = _product()
    request = ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=None,
    )
    admission = admit_controlled_action(request)

    assert admission.decision is AegisDecision.ESCALATE


def test_valid_authority_is_required_to_cross_staged_to_authorized():
    product = _product()
    request = ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=_lease(product),
    )
    admission = admit_controlled_action(request)
    authorized = authorize_product(product, admission)

    assert admission.decision is AegisDecision.ALLOW
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False


def test_expired_authority_cannot_cross_authorization_boundary():
    product = _product()
    request = ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=200.0,
        lease=_lease(product),
    )
    admission = admit_controlled_action(request)

    assert admission.decision is AegisDecision.DENY
    try:
        authorize_product(product, admission)
    except ValueError as exc:
        assert "ALLOW admission" in str(exc)
    else:
        raise AssertionError("expired authority must not authorize the product")
