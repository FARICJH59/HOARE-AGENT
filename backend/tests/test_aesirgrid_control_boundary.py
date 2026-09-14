"""Tests for the AesirGrid execution-admission boundary.

Provenance: 2026-09-14
"""

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    ControlledActionRequest,
)
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode
from hoare_engine.aesirgrid_control_boundary import execute_governed_control


def _request(lease):
    return ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )


def _valid_lease():
    return AuthorityLease(
        lease_id="lease-aesirgrid-001",
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
    )


def test_denied_admission_never_invokes_existing_executor():
    calls = []

    result = execute_governed_control(
        _request(None),
        lambda: calls.append("executed"),
    )

    assert result.admission.decision is AegisDecision.ESCALATE
    assert result.executed is False
    assert calls == []


def test_valid_admission_invokes_executor_once():
    calls = []

    result = execute_governed_control(
        _request(_valid_lease()),
        lambda: calls.append("executed") or {"status": "accepted"},
    )

    assert result.admission.decision is AegisDecision.ALLOW
    assert result.executed is True
    assert result.executor_result == {"status": "accepted"}
    assert calls == ["executed"]


def test_expired_lease_blocks_existing_executor():
    calls = []
    lease = _valid_lease()
    expired = AuthorityLease(
        lease_id=lease.lease_id,
        tenant_id=lease.tenant_id,
        product_id=lease.product_id,
        mode=lease.mode,
        issued_at_s=lease.issued_at_s,
        expires_at_s=150.0,
    )

    result = execute_governed_control(
        _request(expired),
        lambda: calls.append("executed"),
    )

    assert result.admission.decision is AegisDecision.DENY
    assert result.executed is False
    assert calls == []
