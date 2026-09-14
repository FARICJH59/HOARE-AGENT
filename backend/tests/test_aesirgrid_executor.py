"""Tests for executor-neutral AesirGrid admission ordering.

Provenance: 2026-09-14
"""

from hoare_engine.aesirgrid_authority import AuthorityLease, AuthorityStatus, ControlledActionRequest
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode
from hoare_engine.aesirgrid_executor import execute_after_admission


def _lease(**overrides):
    values = dict(
        lease_id="lease-aesirgrid-002",
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )
    values.update(overrides)
    return AuthorityLease(**values)


def _request(lease):
    return ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )


def test_executor_is_not_called_when_authority_is_missing():
    calls = []

    def executor():
        calls.append("called")
        return "executed"

    result = execute_after_admission(_request(None), executor)

    assert result.decision is AegisDecision.ESCALATE
    assert result.result is None
    assert calls == []


def test_executor_is_not_called_when_lease_is_expired():
    calls = []

    def executor():
        calls.append("called")
        return "executed"

    request = _request(_lease(expires_at_s=150.0))
    result = execute_after_admission(request, executor)

    assert result.decision is AegisDecision.DENY
    assert result.result is None
    assert calls == []


def test_executor_is_called_only_after_valid_admission():
    calls = []

    def executor():
        calls.append("called")
        return "executed"

    result = execute_after_admission(_request(_lease()), executor)

    assert result.decision is AegisDecision.ALLOW
    assert result.result == "executed"
    assert result.lease_id == "lease-aesirgrid-002"
    assert calls == ["called"]
