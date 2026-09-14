"""Executor-neutral admission seam for the AesirGrid case study.

Provenance: 2026-09-14

The seam guarantees that the existing executor is invoked only after an
explicit authority lease is validated. It does not implement grid control.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from hoare_engine.aesirgrid_authority import ControlledActionRequest, admit_controlled_action
from hoare_engine.aesirgrid_case_study import AegisDecision

T = TypeVar("T")


@dataclass(frozen=True)
class ExecutionAdmission(Generic[T]):
    decision: AegisDecision
    result: T | None
    reason: str
    lease_id: str | None = None


def execute_after_admission(
    request: ControlledActionRequest,
    executor: Callable[[], T],
) -> ExecutionAdmission[T]:
    """Authorize first, then invoke the caller-supplied existing executor."""

    admission = admit_controlled_action(request)
    if admission.decision is not AegisDecision.ALLOW:
        return ExecutionAdmission(
            decision=admission.decision,
            result=None,
            reason=admission.reason,
            lease_id=admission.lease_id,
        )

    return ExecutionAdmission(
        decision=AegisDecision.ALLOW,
        result=executor(),
        reason="executor invoked after explicit authority admission",
        lease_id=admission.lease_id,
    )


__all__ = ["ExecutionAdmission", "execute_after_admission"]
