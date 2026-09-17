"""HOARE Case Study #1 controlled-mode integration proof.

Provenance: 2026-09-16

This test composes the existing product-factory, synthetic shadow, authority
lease, and executor seam. It proves the boundary without issuing a physical
grid command.
"""

import pytest

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    AuthorityStatus,
    ControlledActionRequest,
    admit_controlled_action,
    authorize_product,
    execute_authorized_action,
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
        evidence_requirements=("telemetry-integrity", "model-verification"),
        deployment_profiles=("simulation", "shadow", "controlled", "live"),
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


def _lease():
    return AuthorityLease(
        lease_id="lease-aesirgrid-e2e-001",
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )


def _request(lease=None):
    return ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )


def test_full_case_study_reaches_authorized_boundary_without_physical_command():
    provider = SyntheticGridTelemetryProvider(
        [
            GridTelemetry("substation-001", 58.0, 2.0, 72.0, 60.01, 1000.0),
            GridTelemetry("substation-002", 104.0, 9.0, 94.0, 59.70, 1000.0),
        ]
    )

    assessments, shadow = run_aesirgrid_shadow(provider)
    product = _product()
    admission = admit_controlled_action(_request(_lease()))
    authorized = authorize_product(product, admission)

    assert len(assessments) == 2
    assert shadow.decision is AegisDecision.ALLOW
    assert shadow.mode is AesirGridMode.SHADOW
    assert admission.decision is AegisDecision.ALLOW
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False


def test_missing_authority_stops_execution_before_executor():
    calls = []

    def existing_executor(request):
        calls.append(request.action)
        return "physical-command-must-not-run"

    with pytest.raises(PermissionError, match="ESCALATE"):
        execute_authorized_action(_request(), existing_executor)

    assert calls == []


def test_wrong_authority_stops_execution_before_executor():
    calls = []

    def existing_executor(request):
        calls.append(request.action)
        return "physical-command-must-not-run"

    wrong_lease = AuthorityLease(
        lease_id="lease-other-product",
        tenant_id="tenant-grid-001",
        product_id="different-product",
        action="apply_maintenance_setpoint",
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
    )

    with pytest.raises(PermissionError, match="DENY"):
        execute_authorized_action(_request(wrong_lease), existing_executor)

    assert calls == []
