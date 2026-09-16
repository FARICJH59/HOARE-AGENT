"""Additional defense-in-depth tests for governed execution.

Provenance: 2026-09-16

These tests verify that a valid authority lease alone is insufficient when a
product definition is supplied: the product must match the request and must
already be explicitly AUTHORIZED. The existing executor remains untouched.
"""

import pytest

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    AuthorityStatus,
    ControlledActionRequest,
    admit_controlled_action,
    authorize_product,
)
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode
from hoare_engine.governed_execution import execute_governed
from hoare_engine.product_factory import ProductLifecycle, build_product_definition


def _product(product_id="aesirgrid-predictive-maintenance"):
    product = build_product_definition(
        product_id=product_id,
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


def _lease(product_id="aesirgrid-predictive-maintenance"):
    return AuthorityLease(
        lease_id="lease-hardening-001",
        tenant_id="tenant-grid-001",
        product_id=product_id,
        action="apply_maintenance_setpoint",
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )


def _request(product_id="aesirgrid-predictive-maintenance"):
    return ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=_lease(product_id),
    )


def test_staged_product_with_valid_lease_cannot_invoke_executor():
    product = _product()
    calls = []

    result = execute_governed(
        _request(),
        lambda: calls.append("executed"),
        product=product,
    )

    assert result.admission.decision is AegisDecision.DENY
    assert result.executed is False
    assert "AUTHORIZED" in result.admission.reason
    assert calls == []


def test_product_identity_mismatch_cannot_invoke_executor():
    product = _product("aesirgrid-product-A")
    calls = []

    request = _request("aesirgrid-product-B")
    result = execute_governed(
        request,
        lambda: calls.append("executed"),
        product=product,
    )

    assert result.admission.decision is AegisDecision.DENY
    assert result.executed is False
    assert "does not match" in result.admission.reason
    assert calls == []


def test_only_authorized_product_reaches_executor():
    product = _product()
    request = _request()
    admission = admit_controlled_action(request)
    authorized = authorize_product(product, admission)
    calls = []

    result = execute_governed(
        request,
        lambda: calls.append("executed") or "accepted",
        product=authorized,
    )

    assert result.admission.decision is AegisDecision.ALLOW
    assert result.executed is True
    assert result.result == "accepted"
    assert calls == ["executed"]


def test_non_allow_admission_never_authorizes_product():
    product = _product()
    request = _request()
    denied = admit_controlled_action(
        ControlledActionRequest(
            tenant_id=request.tenant_id,
            product_id=request.product_id,
            action="disable_protection",
            requested_mode=request.requested_mode,
            now_s=request.now_s,
            lease=request.lease,
        )
    )

    assert denied.decision is AegisDecision.DENY
    with pytest.raises(ValueError, match="ALLOW admission"):
        authorize_product(product, denied)
