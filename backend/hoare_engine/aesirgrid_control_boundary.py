"""Execution-admission boundary for the AesirGrid case study.

Provenance: 2026-09-14

The boundary is deliberately an adapter around an existing executor. It does
not implement or replace physical control. The executor is invoked only after
AEGIS admission succeeds with a valid authority lease.
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
class GovernedExecutionResult:
    admission: ControlledAdmission
    executed: bool
    executor_result: object | None = None


def execute_governed_control(
    request: ControlledActionRequest,
    executor: Callable[[], object],
) -> GovernedExecutionResult:
    """Gate an existing executor; never grant execution authority implicitly."""

    admission = admit_controlled_action(request)
    if admission.decision.value != "ALLOW":
        return GovernedExecutionResult(
            admission=admission,
            executed=False,
        )

    return GovernedExecutionResult(
        admission=admission,
        executed=True,
        executor_result=executor(),
    )


__all__ = ["GovernedExecutionResult", "execute_governed_control"]
