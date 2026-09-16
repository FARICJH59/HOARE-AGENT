"""Executor-neutral execution boundary for HOARE Case Study #1.

Provenance: 2026-09-16

This module is deliberately a seam, not an executor. It requires a successful
AesirGrid authority admission before delegating to an existing executor. No
physical command implementation belongs here.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from hoare_engine.aesirgrid_authority import ControlledActionRequest, admit_controlled_action
from hoare_engine.aesirgrid_case_study import AegisDecision

T = TypeVar("T")


def execute_if_admitted(
    request: ControlledActionRequest,
    executor: Callable[[ControlledActionRequest], T],
) -> T:
    """Delegate to the existing executor only after AEGIS admission."""
    admission = admit_controlled_action(request)
    if admission.decision is not AegisDecision.ALLOW:
        raise PermissionError(
            f"execution not admitted: {admission.decision.value}: {admission.reason}"
        )
    return executor(request)


__all__ = ["execute_if_admitted"]
