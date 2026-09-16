"""Evidence-bound wrapper around the existing governed execution seam.

Provenance: 2026-09-16

This module is additive. It does not replace the existing executor or grant
execution authority to evidence. Evidence is generated from digests and
admission facts; the caller-supplied executor remains the only execution
implementation.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TypeVar

from hoare_engine.aesirgrid_authority import ControlledActionRequest
from hoare_engine.case_study_evidence import EvidenceBundle, build_evidence_bundle, digest_payload
from hoare_engine.governed_execution import GovernedExecutionResult, execute_governed
from hoare_engine.product_factory import ProductDefinition

T = TypeVar("T")


@dataclass(frozen=True)
class EvidenceBoundExecutionResult:
    execution: GovernedExecutionResult
    evidence: EvidenceBundle


def execute_governed_with_evidence(
    request: ControlledActionRequest,
    executor: Callable[[], T],
    *,
    product: ProductDefinition,
    case_study_id: str,
    telemetry_payload: object,
    evidence: Iterable[str],
    event_fields: dict[str, object] | None = None,
) -> EvidenceBoundExecutionResult:
    """Create non-secret evidence for a governed execution attempt."""

    execution = execute_governed(request, executor, product=product)
    bundle = build_evidence_bundle(
        case_study_id=case_study_id,
        product_id=request.product_id,
        tenant_id=request.tenant_id,
        mode=request.requested_mode,
        decision=execution.admission.decision,
        evidence=evidence,
        telemetry_digest=digest_payload(telemetry_payload),
        authority_lease_id=execution.admission.lease_id,
        event_fields={
            "action": request.action,
            "executed": execution.executed,
            **(event_fields or {}),
        },
    )
    return EvidenceBoundExecutionResult(execution=execution, evidence=bundle)


__all__ = ["EvidenceBoundExecutionResult", "execute_governed_with_evidence"]
