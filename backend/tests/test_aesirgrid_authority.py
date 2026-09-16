"""Tests for the explicit AesirGrid controlled/live authority boundary.

Provenance: 2026-09-16
"""

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    AuthorityStatus,
    ControlledActionRequest,
    admit_controlled_action,
)
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode


def _lease(**overrides):
    values = dict(
        lease_id="lease-aesirgrid-001",
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
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


def test_controlled_action_requires_explicit_valid_lease():
    result = admit_controlled_action(_request(lease=None))
    assert result.decision is AegisDecision.ESCALATE
    assert "authority lease required" in result.reason


def test_valid_controlled_lease_allows_admission():
    result = admit_controlled_action(_request())
    assert result.decision is AegisDecision.ALLOW
    assert result.lease_id == "lease-aesirgrid-001"


def test_unrelated_action_is_denied_even_with_valid_lease():
    result = admit_controlled_action(_request(action="disable_protection"))
    assert result.decision is AegisDecision.DENY
    assert "action mismatch" in result.reason


def test_expired_lease_is_denied():
    result = admit_controlled_action(_request(now_s=200.0))
    assert result.decision is AegisDecision.DENY
    assert "expired" in result.reason


def test_revoked_lease_is_denied():
    result = admit_controlled_action(
        _request(lease=_lease(status=AuthorityStatus.REVOKED))
    )
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
    result = admit_controlled_action(
        _request(requested_mode=AesirGridMode.SIMULATION)
    )
    assert result.decision is AegisDecision.DENY
    assert "CONTROLLED or LIVE" in result.reason


def test_malformed_lease_action_fails_closed():
    result = admit_controlled_action(_request(lease=_lease(action=None)))
    assert result.decision is AegisDecision.DENY
    assert "lease action is required" in result.reason
