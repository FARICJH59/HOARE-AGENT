"""Tests proving authorization occurs before executor invocation.

Provenance: 2026-09-12
"""

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    AuthorityStatus,
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
        status=AuthorityStatus.VALID,
    )


def test_denied_admission_never_invokes_executor():
    calls = []

    def executor(request):
        calls.append(request)
        return "executed"

    result = execute_governed_control(_request(None), executor)

    assert result.admission.decision is AegisDecision.ESCALATE
    assert result.executed is False
    assert result.executor_result is None
    assert calls == []


def test_allowed_admission_invokes_injected_existing_executor_once():
    calls = []

    def executor(request):
        calls.append(request)
        return {"accepted": True, "action": request.action}

    result = execute_governed_control(_request(_valid_lease()), executor)

    assert result.admission.decision is AegisDecision.ALLOW
    assert result.executed is True
    assert result.executor_result == {
        "accepted": True,
        "action": "apply_maintenance_setpoint",
    }
    assert len(calls) == 1


def test_expired_lease_blocks_existing_executor():
    calls = []
    expired = AuthorityLease(
        lease_id="lease-expired",
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=150.0,
        status=AuthorityStatus.VALID,
    )

    def executor(request):
        calls.append(request)
        return "should-not-run"

    result = execute_governed_control(_request(expired), executor)

    assert result.admission.decision is AegisDecision.DENY
    assert result.executed is False
    assert calls == []
