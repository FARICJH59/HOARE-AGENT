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
from hoare_engine.product_factory import ProductDefinition, ProductLifecycle

T = TypeVar("T")


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
    """Admit through AEGIS before invoking the caller-supplied executor.

    When a product definition is supplied, controlled execution additionally
    requires the product to have crossed STAGED -> AUTHORIZED through the
    explicit authority boundary. The optional argument preserves compatibility
    with existing executor-neutral callers while allowing vertical case
    studies to prove the full lifecycle boundary.
    """

    admission = admit_controlled_action(request)
    if admission.decision.value != "ALLOW":
        return GovernedExecutionResult(admission=admission, executed=False)

    if product is not None:
        if product.product_id != request.product_id:
            denied = ControlledAdmission(
                decision=admission.decision.DENY,
                reason="product definition does not match execution request",
                lease_id=admission.lease_id,
            )
            return GovernedExecutionResult(admission=denied, executed=False)
        if product.lifecycle_state is not ProductLifecycle.AUTHORIZED:
            denied = ControlledAdmission(
                decision=admission.decision.DENY,
                reason="product must be AUTHORIZED before governed execution",
                lease_id=admission.lease_id,
            )
            return GovernedExecutionResult(admission=denied, executed=False)

    return GovernedExecutionResult(
        admission=admission,
        executed=True,
        result=executor(),
    )


__all__ = ["GovernedExecutionResult", "execute_governed"]
