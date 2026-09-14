"""Executor-neutral AEGIS admission seam.

Provenance: 2026-09-14

The existing executor remains the implementation authority. This module only
controls whether an already-defined executor may be invoked.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from hoare_engine.aesirgrid_authority import (
    ControlledActionRequest,
    ControlledAdmission,
    admit_controlled_action,
)

T = TypeVar("T")


@dataclass(frozen=True)
class GovernedExecutionResult:
    admission: ControlledAdmission
    executed: bool
    result: object | None = None


def execute_governed(
    request: ControlledActionRequest,
    executor: Callable[[], T],
) -> GovernedExecutionResult:
    """Admit through AEGIS before invoking the caller-supplied executor."""

    admission = admit_controlled_action(request)
    if admission.decision.value != "ALLOW":
        return GovernedExecutionResult(admission=admission, executed=False)

    return GovernedExecutionResult(
        admission=admission,
        executed=True,
        result=executor(),
    )


__all__ = ["GovernedExecutionResult", "execute_governed"]
