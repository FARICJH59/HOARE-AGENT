"""Admission-boundary case study tests.

Provenance: 2026-09-16

These tests model the security property that matters at the controlled
boundary: an action reaches the existing executor only after AEGIS admission.
The harness uses a recording executor stand-in and never sends a physical
command.
"""

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    AuthorityStatus,
    ControlledActionRequest,
    admit_controlled_action,
)
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode


class RecordingExecutor:
    def __init__(self):
        self.calls = []

    def execute(self, action: str) -> None:
        self.calls.append(action)


def _lease(**overrides):
    values = dict(
        lease_id="lease-001",
        tenant_id="tenant-001",
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
        tenant_id="tenant-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )


def _governed_execute(request, executor):
    admission = admit_controlled_action(request)
    if admission.decision is AegisDecision.ALLOW:
        executor.execute(request.action)
    return admission


def test_no_lease_escalates_and_executor_is_not_called():
    executor = RecordingExecutor()
    admission = _governed_execute(_request(None), executor)

    assert admission.decision is AegisDecision.ESCALATE
    assert executor.calls == []


def test_wrong_tenant_denies_and_executor_is_not_called():
    executor = RecordingExecutor()
    request = _request(_lease(tenant_id="other-tenant"))

    admission = _governed_execute(request, executor)

    assert admission.decision is AegisDecision.DENY
    assert executor.calls == []


def test_expired_lease_denies_and_executor_is_not_called():
    executor = RecordingExecutor()
    request = _request(_lease(expires_at_s=150.0))

    admission = _governed_execute(request, executor)

    assert admission.decision is AegisDecision.DENY
    assert executor.calls == []


def test_valid_lease_is_the_only_case_that_reaches_executor_boundary():
    executor = RecordingExecutor()
    request = _request(_lease())

    admission = _governed_execute(request, executor)

    assert admission.decision is AegisDecision.ALLOW
    assert executor.calls == ["apply_maintenance_setpoint"]


def test_live_request_without_live_lease_is_denied():
    executor = RecordingExecutor()
    request = ControlledActionRequest(
        tenant_id="tenant-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.LIVE,
        now_s=150.0,
        lease=_lease(mode=AesirGridMode.CONTROLLED),
    )

    admission = _governed_execute(request, executor)

    assert admission.decision is AegisDecision.DENY
    assert executor.calls == []
