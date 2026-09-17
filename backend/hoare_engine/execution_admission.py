"""Canonical execution-admission contract for HOARE.

Provenance: 2026-09-17

This module defines the vertical-neutral seam between HOARE governance and
an existing executor. It deliberately does not implement execution.

Execution principle:
    AGENT -> HOARE/PASOR -> AEGIS -> admission -> existing executor -> target

Vertical-specific authority systems may implement the admission protocol.
The canonical helper below prevents an executor from being invoked unless the
adapter explicitly returns an ALLOW decision.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Generic, Protocol, TypeVar


T = TypeVar("T")


class ExecutionDecision(str, Enum):
    """Canonical execution decision exposed by a governance adapter."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class ExecutionAdmission:
    """Provider-neutral result of an execution-admission check."""

    decision: ExecutionDecision
    reason: str
    authority_id: str | None = None


class ExecutionAdmissionAuthority(Protocol):
    """Adapter contract implemented by a vertical-specific authority layer."""

    def admit(self, request: object) -> ExecutionAdmission:
        """Return ALLOW only when execution is authorized for the request."""
        ...


class ExecutionNotAdmitted(PermissionError):
    """Raised when canonical admission does not grant execution."""


def execute_admitted(
    request: object,
    authority: ExecutionAdmissionAuthority,
    executor: Callable[[object], T],
) -> T:
    """Invoke an existing executor only after canonical admission succeeds.

    The executor is never called for DENY or ESCALATE. The executor remains
    outside this module and remains the implementation authority for its target.
    """

    admission = authority.admit(request)
    if admission.decision is not ExecutionDecision.ALLOW:
        raise ExecutionNotAdmitted(
            f"execution not admitted: {admission.decision.value}: {admission.reason}"
        )
    return executor(request)


__all__ = [
    "ExecutionAdmission",
    "ExecutionAdmissionAuthority",
    "ExecutionDecision",
    "ExecutionNotAdmitted",
    "execute_admitted",
]