"""Integrated Case Study #1 authorization/execution proof.

Provenance: 2026-09-16

The executor is deliberately a test double. The test proves the governance
boundary, not physical grid control.
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
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode
from hoare_engine.product_factory import ProductLifecycle, build_product_definition


def _staged_product():
    product = build_product_definition(
        product_id="aesirgrid-predictive-maintenance",
        product_version="1.0.0",
        domain="energy",
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


def _lease(**overrides):
    values = dict(
        lease_id="lease-aesirgrid-controlled-001",
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )
    values.update(overrides)
    return AuthorityLease(**values)


def _request(**overrides):
    values = dict(
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=_lease(),
    )
    values.update(overrides)
    return ControlledActionRequest(**values)


def test_case_study_controlled_path_is_staged_authorized_then_delegated():
    product = _staged_product()
    request = _request()

    admission = admit_controlled_action(request)
    authorized = authorize_product(product, admission)

    calls = []

    def existing_executor(received):
        calls.append(received)
        return {"accepted": True, "action": received.action}

    result = execute_authorized_action(request, existing_executor)

    assert admission.decision is AegisDecision.ALLOW
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False
    assert result == {"accepted": True, "action": "apply_maintenance_setpoint"}
    assert calls == [request]


def test_case_study_escalation_blocks_executor_until_authority_exists():
    calls = []

    def existing_executor(received):
        calls.append(received)
        return "must-not-run"

    request = _request(lease=None)
    admission = admit_controlled_action(request)

    assert admission.decision is AegisDecision.ESCALATE
    with pytest.raises(PermissionError, match="ESCALATE"):
        execute_authorized_action(request, existing_executor)
    assert calls == []


def test_case_study_cross_tenant_authority_is_denied_and_executor_is_not_called():
    calls = []

    def existing_executor(received):
        calls.append(received)
        return "must-not-run"

    request = _request(tenant_id="tenant-attacker")
    admission = admit_controlled_action(request)

    assert admission.decision is AegisDecision.DENY
    with pytest.raises(PermissionError, match="DENY"):
        execute_authorized_action(request, existing_executor)
    assert calls == []


def test_case_study_expired_authority_is_denied_and_executor_is_not_called():
    calls = []

    def existing_executor(received):
        calls.append(received)
        return "must-not-run"

    request = _request(now_s=200.0)
    admission = admit_controlled_action(request)

    assert admission.decision is AegisDecision.DENY
    with pytest.raises(PermissionError, match="DENY"):
        execute_authorized_action(request, existing_executor)
    assert calls == []
