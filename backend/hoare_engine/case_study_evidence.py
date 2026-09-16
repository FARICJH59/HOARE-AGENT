"""Evidence bundle for auditable HOARE case-study decisions.

Provenance: 2026-09-16

The bundle records hashes and governance facts, not credentials or raw customer
payloads. It is suitable for an audit trail while keeping customer data and
secrets outside the evidence artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable

from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode


@dataclass(frozen=True)
class EvidenceBundle:
    case_study_id: str
    product_id: str
    tenant_id: str
    mode: AesirGridMode
    decision: AegisDecision
    evidence: tuple[str, ...]
    telemetry_digest: str
    authority_lease_id: str | None
    event_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "case_study_id": self.case_study_id,
            "product_id": self.product_id,
            "tenant_id": self.tenant_id,
            "mode": self.mode.value,
            "decision": self.decision.value,
            "evidence": list(self.evidence),
            "telemetry_digest": self.telemetry_digest,
            "authority_lease_id": self.authority_lease_id,
            "event_digest": self.event_digest,
        }


def digest_payload(payload: object) -> str:
    """Return a stable SHA-256 digest without retaining the payload."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_evidence_bundle(
    *,
    case_study_id: str,
    product_id: str,
    tenant_id: str,
    mode: AesirGridMode,
    decision: AegisDecision,
    evidence: Iterable[str],
    telemetry_digest: str,
    authority_lease_id: str | None,
    event_fields: dict[str, object],
) -> EvidenceBundle:
    """Build a non-secret evidence record for a governed case-study event."""

    normalized = tuple(dict.fromkeys(item.strip() for item in evidence if item.strip()))
    event_digest = digest_payload(
        {
            "case_study_id": case_study_id,
            "product_id": product_id,
            "tenant_id": tenant_id,
            "mode": mode.value,
            "decision": decision.value,
            "evidence": normalized,
            "telemetry_digest": telemetry_digest,
            "authority_lease_id": authority_lease_id,
            "event_fields": event_fields,
        }
    )
    return EvidenceBundle(
        case_study_id=case_study_id,
        product_id=product_id,
        tenant_id=tenant_id,
        mode=mode,
        decision=decision,
        evidence=normalized,
        telemetry_digest=telemetry_digest,
        authority_lease_id=authority_lease_id,
        event_digest=event_digest,
    )


__all__ = ["EvidenceBundle", "build_evidence_bundle", "digest_payload"]
