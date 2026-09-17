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
    """Adapt the existing AesirGrid authority to the canonical contract.

    The raw admission is retained only for this synchronous call so the
    compatibility result can preserve the existing ``ControlledAdmission``
    object without evaluating the authority twice.
    """

    def __init__(self) -> None:
        self.raw_admission: ControlledAdmission | None = None

    def admit(self, request: object) -> ExecutionAdmission:
        if not isinstance(request, ControlledActionRequest):
            raise TypeError("AesirGrid authority requires ControlledActionRequest")

        raw = admit_controlled_action(request)
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

    When a product definition is supplied, controlled execution additionally
    requires the product to have crossed STAGED -> AUTHORIZED through the
    explicit authority boundary. The optional argument preserves compatibility
    with existing executor-neutral callers while allowing vertical case
    studies to prove the full lifecycle boundary.
    """

    if product is not None:
        if product.product_id != request.product_id:
            denied = ControlledAdmission(
                decision=AegisDecision.DENY,
                reason="product definition does not match execution request",
                lease_id=request.lease.lease_id if request.lease is not None else None,
            )
            return GovernedExecutionResult(admission=denied, executed=False)
        if product.lifecycle_state is not ProductLifecycle.AUTHORIZED:
            denied = ControlledAdmission(
                decision=AegisDecision.DENY,
                reason="product must be AUTHORIZED before governed execution",
                lease_id=request.lease.lease_id if request.lease is not None else None,
            )
            return GovernedExecutionResult(admission=denied, executed=False)

    authority = _AesirGridAdmissionAuthority()
    try:
        result = execute_admitted(
            request,
            authority,
            lambda _request: executor(),
        )
    except PermissionError:
        if authority.raw_admission is None:
            raise
        return GovernedExecutionResult(
            admission=authority.raw_admission,
            executed=False,
        )

    if authority.raw_admission is None:
        raise RuntimeError("canonical admission completed without an admission result")

    return GovernedExecutionResult(
        admission=authority.raw_admission,
        executed=True,
        result=result,
    )


__all__ = ["GovernedExecutionResult", "execute_governed"]
