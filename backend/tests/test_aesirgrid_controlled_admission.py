"""End-to-end admission harness for HOARE Case Study #1.

Provenance: 2026-09-16

This test composes the existing product-factory and synthetic AesirGrid
layers with the explicit authority lease boundary and an injected executor.
It proves the governance boundary without invoking physical infrastructure.
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


def _staged_product():
    product = build_product_definition(
        product_id="aesirgrid-predictive-maintenance",
        product_version="1.0.0",
        domain="energy",
        capabilities=("Telemetry", "PredictiveMaintenance"),
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


def _provider():
    return SyntheticGridTelemetryProvider(
        [
            GridTelemetry("substation-001", 58.0, 2.0, 72.0, 60.01, 1000.0),
            GridTelemetry("substation-002", 104.0, 9.0, 94.0, 59.70, 1000.0),
        ]
    )


def _lease():
    return AuthorityLease(
        lease_id="lease-aesirgrid-001",
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )


def test_case_study_shadow_to_authorized_to_existing_executor():
    assessments, shadow = run_aesirgrid_shadow(_provider())

    assert shadow.decision is AegisDecision.ALLOW
    assert shadow.mode is AesirGridMode.SHADOW
    assert any(item.anomaly for item in assessments)

    request = ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=_lease(),
    )
    admission = admit_controlled_action(request)
    authorized = authorize_product(_staged_product(), admission)

    calls = []

    def existing_executor(control_request):
        calls.append(control_request.action)
        return "controlled-execution-simulated"

    result = execute_authorized_action(request, existing_executor)

    assert admission.decision is AegisDecision.ALLOW
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False
    assert result == "controlled-execution-simulated"
    assert calls == ["apply_maintenance_setpoint"]


def test_case_study_missing_authority_escalates_and_never_executes():
    request = ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=None,
    )
    calls = []

    def existing_executor(control_request):
        calls.append(control_request.action)
        return "must-not-run"

    admission = admit_controlled_action(request)
    assert admission.decision is AegisDecision.ESCALATE

    with pytest.raises(PermissionError, match="ESCALATE"):
        execute_authorized_action(request, existing_executor)

    assert calls == []


def test_case_study_wrong_tenant_denies_and_never_executes():
    request = ControlledActionRequest(
        tenant_id="attacker-tenant",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=_lease(),
    )
    calls = []

    def existing_executor(control_request):
        calls.append(control_request.action)
        return "must-not-run"

    admission = admit_controlled_action(request)
    assert admission.decision is AegisDecision.DENY

    with pytest.raises(PermissionError, match="DENY"):
        execute_authorized_action(request, existing_executor)

    assert calls == []
