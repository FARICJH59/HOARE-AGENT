"""Executor-neutral controlled-action boundary for AesirGrid.

Provenance: 2026-09-12

The existing executor remains untouched. This adapter performs admission first
and invokes an injected executor only after an explicit authority lease is
accepted.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from hoare_engine.aesirgrid_authority import (
    ControlledActionRequest,
    ControlledAdmission,
    admit_controlled_action,
)


@dataclass(frozen=True)
class ControlBoundaryResult:
    admission: ControlledAdmission
    executed: bool
    executor_result: object | None = None


def execute_governed_control(
    request: ControlledActionRequest,
    executor: Callable[[ControlledActionRequest], object],
) -> ControlBoundaryResult:
    """Authorize before invoking the existing executor.

    The executor is dependency-injected so HOARE does not acquire a second
    physical execution implementation merely for the case study.
    """

    admission = admit_controlled_action(request)
    if admission.decision.value != "ALLOW":
        return ControlBoundaryResult(admission=admission, executed=False)

    result = executor(request)
    return ControlBoundaryResult(
        admission=admission,
        executed=True,
        executor_result=result,
    )


__all__ = ["ControlBoundaryResult", "execute_governed_control"]
