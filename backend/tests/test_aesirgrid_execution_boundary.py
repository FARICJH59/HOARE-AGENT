"""Focused test for the executor-neutral AEGIS boundary.

Provenance: 2026-09-16
"""

from hoare_engine.aesirgrid_authority import AuthorityLease, AuthorityStatus, ControlledActionRequest
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode
from hoare_engine.aesirgrid_execution_boundary import execute_if_admitted


def _request(lease):
    return ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )


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


def test_allow_delegates_exactly_once_to_existing_executor():
    calls = []

    def executor(request):
        calls.append(request.action)
        return "simulated-result"

    result = execute_if_admitted(_request(_lease()), executor)

    assert result == "simulated-result"
    assert calls == ["apply_maintenance_setpoint"]


def test_escalation_never_reaches_executor():
    calls = []

    def executor(request):
        calls.append(request.action)
        return "must-not-run"

    request = _request(None)
    try:
        execute_if_admitted(request, executor)
    except PermissionError as exc:
        assert "ESCALATE" in str(exc)
    else:
        raise AssertionError("missing lease must escalate")

    assert calls == []


def test_deny_never_reaches_executor():
    calls = []

    def executor(request):
        calls.append(request.action)
        return "must-not-run"

    request = _request(_lease(tenant_id="other-tenant"))
    try:
        execute_if_admitted(request, executor)
    except PermissionError as exc:
        assert "DENY" in str(exc)
    else:
        raise AssertionError("tenant mismatch must deny")

    assert calls == []
