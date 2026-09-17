"""Executor-neutral canonical execution seam.

Provenance: 2026-09-17

The existing executor remains the implementation authority. This module
controls whether an already-defined executor may be invoked and adapts the
existing AesirGrid authority to HOARE's vertical-neutral admission contract.
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
from hoare_engine.aesirgrid_case_study import AegisDecision
from hoare_engine.execution_admission import (
    ExecutionAdmission,
    ExecutionAdmissionAuthority,
    ExecutionDecision,
    execute_admitted,
)
from hoare_engine.product_factory import ProductDefinition, ProductLifecycle

T = TypeVar("T")


class _AesirGridAdmissionAuthority:
    """Adapt existing AesirGrid authority to the canonical admission contract."""

    def __init__(self, product: ProductDefinition | None = None) -> None:
        self.product = product
        self.raw_admission: ControlledAdmission | None = None

    def admit(self, request: object) -> ExecutionAdmission:
        if not isinstance(request, ControlledActionRequest):
            raise TypeError("AesirGrid authority requires ControlledActionRequest")

        raw = admit_controlled_action(request)

        if raw.decision is AegisDecision.ALLOW and self.product is not None:
            if self.product.product_id != request.product_id:
                raw = ControlledAdmission(
                    decision=AegisDecision.DENY,
                    reason="product definition does not match execution request",
                    lease_id=raw.lease_id,
                )
            elif self.product.lifecycle_state is not ProductLifecycle.AUTHORIZED:
                raw = ControlledAdmission(
                    decision=AegisDecision.DENY,
                    reason="product must be AUTHORIZED before governed execution",
                    lease_id=raw.lease_id,
                )

        self.raw_admission = raw
        return ExecutionAdmission(
            decision=ExecutionDecision(raw.decision.value),
            reason=raw.reason,
            authority_id=raw.lease_id,
        )


@dataclass(frozen=True)
class GovernedExecutionResult:
    admission: ControlledAdmission
    executed: bool
    result: object | None = None


def execute_governed(
    request: ControlledActionRequest,
    executor: Callable[[], T],
    *,
    product: ProductDefinition | None = None,
) -> GovernedExecutionResult:
    """Admit through the canonical seam before invoking the existing executor.

    The AesirGrid authority is evaluated exactly once. Product lifecycle and
    identity checks are part of that admission before the executor can run.
    """

    authority: ExecutionAdmissionAuthority = _AesirGridAdmissionAuthority(product)
    authority_impl = authority

    try:
        result = execute_admitted(
            request,
            authority,
            lambda _request: executor(),
        )
    except PermissionError:
        raw_admission = authority_impl.raw_admission  # type: ignore[attr-defined]
        if raw_admission is None:
            raise RuntimeError("canonical admission failed without an admission result")
        return GovernedExecutionResult(
            admission=raw_admission,
            executed=False,
        )

    raw_admission = authority_impl.raw_admission  # type: ignore[attr-defined]
    if raw_admission is None:
        raise RuntimeError("canonical admission completed without an admission result")

    return GovernedExecutionResult(
        admission=raw_admission,
        executed=True,
        result=result,
    )


__all__ = ["GovernedExecutionResult", "execute_governed"]
