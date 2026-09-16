"""Tests for the explicit AesirGrid controlled/live authority boundary.

Provenance: 2026-09-14
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
from hoare_engine.product_factory import ProductLifecycle, build_product_definition


def _lease(**overrides):
    values = dict(
        lease_id="lease-aesirgrid-001",
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


def _staged_product():
    product = build_product_definition(
        product_id="aesirgrid-predictive-maintenance",
        product_version="1.0.0",
        domain="energy",
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


def test_controlled_action_requires_explicit_valid_lease():
    result = admit_controlled_action(_request(lease=None))
    assert result.decision is AegisDecision.ESCALATE
    assert "authority lease required" in result.reason


def test_valid_controlled_lease_allows_admission():
    result = admit_controlled_action(_request())
    assert result.decision is AegisDecision.ALLOW
    assert result.lease_id == "lease-aesirgrid-001"


def test_expired_lease_is_denied():
    result = admit_controlled_action(_request(now_s=200.0))
    assert result.decision is AegisDecision.DENY
    assert "expired" in result.reason


def test_revoked_lease_is_denied():
    result = admit_controlled_action(_request(lease=_lease(status=AuthorityStatus.REVOKED)))
    assert result.decision is AegisDecision.DENY
    assert "expired or revoked" in result.reason


def test_tenant_mismatch_is_denied():
    result = admit_controlled_action(_request(tenant_id="attacker-tenant"))
    assert result.decision is AegisDecision.DENY
    assert "tenant mismatch" in result.reason


def test_product_mismatch_is_denied():
    result = admit_controlled_action(_request(product_id="different-product"))
    assert result.decision is AegisDecision.DENY
    assert "product mismatch" in result.reason


def test_mode_mismatch_is_denied():
    result = admit_controlled_action(
        _request(
            requested_mode=AesirGridMode.LIVE,
            lease=_lease(mode=AesirGridMode.CONTROLLED),
        )
    )
    assert result.decision is AegisDecision.DENY
    assert "mode mismatch" in result.reason


def test_simulation_cannot_use_controlled_admission_boundary():
    result = admit_controlled_action(_request(requested_mode=AesirGridMode.SIMULATION))
    assert result.decision is AegisDecision.DENY
    assert "CONTROLLED or LIVE" in result.reason


def test_allow_admission_moves_staged_product_to_authorized():
    product = _staged_product()
    admission = admit_controlled_action(_request())

    authorized = authorize_product(product, admission)

    assert admission.decision is AegisDecision.ALLOW
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.authority == "product-definition-only"
    assert authorized.can_execute is False


def test_non_allow_admission_cannot_authorize_product():
    product = _staged_product()
    admission = admit_controlled_action(_request(lease=None))

    assert admission.decision is AegisDecision.ESCALATE
    with pytest.raises(ValueError, match="ALLOW admission"):
        authorize_product(product, admission)


def test_authorization_cannot_skip_staged_state():
    product = build_product_definition(
        product_id="aesirgrid-predictive-maintenance",
        product_version="1.0.0",
        domain="energy",
    )
    admission = admit_controlled_action(_request())

    with pytest.raises(ValueError, match="STAGED"):
        authorize_product(product, admission)
