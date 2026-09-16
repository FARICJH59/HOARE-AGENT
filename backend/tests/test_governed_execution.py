"""Tests for the executor-neutral governance seam.

Provenance: 2026-09-16
"""

from hoare_engine.aesirgrid_authority import AuthorityLease, AuthorityStatus, ControlledActionRequest
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode
from hoare_engine.governed_execution import execute_governed


def _request(lease=None, now_s=150.0):
    return ControlledActionRequest(
        tenant_id="tenant-grid-001", product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint", requested_mode=AesirGridMode.CONTROLLED,
        now_s=now_s, lease=lease,
    )


def _valid_lease():
    return AuthorityLease(
        lease_id="lease-aesirgrid-001", tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance", action="apply_maintenance_setpoint",
        mode=AesirGridMode.CONTROLLED, issued_at_s=100.0, expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )


def test_executor_is_not_called_when_authority_is_missing():
    calls = []
    result = execute_governed(_request(), lambda: calls.append("executed"))
    assert result.admission.decision is AegisDecision.ESCALATE
    assert result.executed is False
    assert calls == []


def test_existing_executor_is_called_only_after_allow():
    calls = []
    result = execute_governed(_request(lease=_valid_lease()), lambda: calls.append("executed") or "executor-result")
    assert result.admission.decision is AegisDecision.ALLOW
    assert result.executed is True
    assert result.result == "executor-result"
    assert calls == ["executed"]


def test_expired_authority_prevents_executor_call():
    calls = []
    result = execute_governed(_request(lease=_valid_lease(), now_s=200.0), lambda: calls.append("executed"))
    assert result.admission.decision is AegisDecision.DENY
    assert result.executed is False
    assert calls == []
