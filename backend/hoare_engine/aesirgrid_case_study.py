"""Provider-neutral AesirGrid simulation/shadow workflow for HOARE.

Provenance: 2026-09-12

This module is intentionally deterministic and synthetic. It exercises the
control-plane path without connecting to a real grid, replacing an executor,
or authorizing live physical control.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Sequence


class AegisDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


class AesirGridMode(str, Enum):
    SIMULATION = "SIMULATION"
    SHADOW = "SHADOW"
    CONTROLLED = "CONTROLLED"
    LIVE = "LIVE"


@dataclass(frozen=True)
class GridTelemetry:
    asset_id: str
    temperature_c: float
    vibration_mm_s: float
    load_pct: float
    frequency_hz: float
    timestamp_s: float


@dataclass(frozen=True)
class HealthAssessment:
    asset_id: str
    health_score: float
    anomaly: bool
    confidence: float
    reason: str


@dataclass(frozen=True)
class GovernanceDecision:
    decision: AegisDecision
    mode: AesirGridMode
    reason: str
    evidence: tuple[str, ...]


class TelemetryProvider(Protocol):
    def read(self) -> Sequence[GridTelemetry]:
        """Return telemetry for the requested execution context."""


class SyntheticGridTelemetryProvider:
    """Deterministic telemetry provider used by the case study."""

    def __init__(self, samples: Sequence[GridTelemetry]) -> None:
        self._samples = tuple(samples)

    def read(self) -> Sequence[GridTelemetry]:
        return self._samples


def assess_asset(sample: GridTelemetry) -> HealthAssessment:
    """Compute a deterministic maintenance score from synthetic telemetry."""

    if not sample.asset_id.strip():
        raise ValueError("asset_id is required")
    if sample.temperature_c < -40 or sample.temperature_c > 150:
        raise ValueError("temperature outside supported telemetry range")
    if sample.vibration_mm_s < 0 or sample.load_pct < 0 or sample.load_pct > 100:
        raise ValueError("invalid telemetry range")
    if sample.frequency_hz <= 0 or sample.timestamp_s < 0:
        raise ValueError("invalid frequency or timestamp")

    penalties = 0.0
    reasons: list[str] = []

    if sample.temperature_c > 90:
        penalties += 0.30
        reasons.append("high-temperature")
    if sample.vibration_mm_s > 7:
        penalties += 0.30
        reasons.append("high-vibration")
    if sample.load_pct > 90:
        penalties += 0.15
        reasons.append("high-load")
    if abs(sample.frequency_hz - 60.0) > 0.15:
        penalties += 0.20
        reasons.append("frequency-deviation")

    score = max(0.0, min(1.0, 1.0 - penalties))
    anomaly = score < 0.70
    confidence = 0.98 if anomaly else 0.95
    reason = ",".join(reasons) if reasons else "nominal"

    return HealthAssessment(
        asset_id=sample.asset_id,
        health_score=score,
        anomaly=anomaly,
        confidence=confidence,
        reason=reason,
    )


def evaluate_aegis(
    *,
    mode: AesirGridMode,
    assessments: Sequence[HealthAssessment],
    telemetry_fresh: bool,
    evidence_complete: bool,
) -> GovernanceDecision:
    """Apply the case-study governance boundary without executing control."""

    evidence = ["telemetry-integrity", "model-verification"]
    if evidence_complete:
        evidence.append("evidence-complete")

    if not telemetry_fresh:
        return GovernanceDecision(
            decision=AegisDecision.DENY,
            mode=mode,
            reason="stale telemetry",
            evidence=tuple(evidence),
        )

    if not evidence_complete:
        return GovernanceDecision(
            decision=AegisDecision.DENY,
            mode=mode,
            reason="required evidence is incomplete",
            evidence=tuple(evidence),
        )

    if any(item.confidence < 0.90 for item in assessments):
        return GovernanceDecision(
            decision=AegisDecision.ESCALATE,
            mode=mode,
            reason="model confidence requires human authority",
            evidence=tuple(evidence),
        )

    if mode is AesirGridMode.SIMULATION:
        return GovernanceDecision(
            decision=AegisDecision.ALLOW,
            mode=mode,
            reason="simulation analysis permitted",
            evidence=tuple(evidence),
        )

    if mode is AesirGridMode.SHADOW:
        return GovernanceDecision(
            decision=AegisDecision.ALLOW,
            mode=mode,
            reason="shadow analysis permitted; no physical control",
            evidence=tuple(evidence),
        )

    return GovernanceDecision(
        decision=AegisDecision.ESCALATE,
        mode=mode,
        reason="controlled/live operation requires explicit authority",
        evidence=tuple(evidence),
    )


def run_aesirgrid_shadow(
    provider: TelemetryProvider,
    *,
    telemetry_fresh: bool = True,
    evidence_complete: bool = True,
) -> tuple[tuple[HealthAssessment, ...], GovernanceDecision]:
    """Run synthetic telemetry through analysis and AEGIS shadow governance."""

    samples = tuple(provider.read())
    assessments = tuple(assess_asset(sample) for sample in samples)
    decision = evaluate_aegis(
        mode=AesirGridMode.SHADOW,
        assessments=assessments,
        telemetry_fresh=telemetry_fresh,
        evidence_complete=evidence_complete,
    )
    return assessments, decision


__all__ = [
    "AegisDecision",
    "AesirGridMode",
    "GridTelemetry",
    "HealthAssessment",
    "GovernanceDecision",
    "SyntheticGridTelemetryProvider",
    "TelemetryProvider",
    "assess_asset",
    "evaluate_aegis",
    "run_aesirgrid_shadow",
]
