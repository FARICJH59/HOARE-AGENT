"""HOARE Case Study #2: governed industrial robotics inspection.

Provenance: 2026-09-16

This case deliberately uses a different vertical from AesirGrid while reusing
HOARE's product-factory and governance concepts. It is deterministic and
synthetic and never commands a physical robot.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Sequence


class RoboticsMode(str, Enum):
    SIMULATION = "SIMULATION"
    SHADOW = "SHADOW"
    CONTROLLED = "CONTROLLED"


class RoboticsDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class RobotTelemetry:
    robot_id: str
    joint_temperature_c: float
    vibration_mm_s: float
    cycle_time_s: float
    payload_pct: float
    timestamp_s: float


@dataclass(frozen=True)
class InspectionAssessment:
    robot_id: str
    health_score: float
    maintenance_signal: bool
    confidence: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RoboticsGovernanceDecision:
    decision: RoboticsDecision
    mode: RoboticsMode
    reason: str
    evidence: tuple[str, ...]


class RobotTelemetryProvider(Protocol):
    def read(self) -> Sequence[RobotTelemetry]:
        """Return telemetry for the requested robot context."""


class SyntheticRobotTelemetryProvider:
    def __init__(self, samples: Sequence[RobotTelemetry]) -> None:
        self._samples = tuple(samples)

    def read(self) -> Sequence[RobotTelemetry]:
        return self._samples


def inspect_robot(sample: RobotTelemetry) -> InspectionAssessment:
    if not sample.robot_id.strip():
        raise ValueError("robot_id is required")
    if sample.joint_temperature_c < -20 or sample.joint_temperature_c > 140:
        raise ValueError("joint temperature outside supported telemetry range")
    if sample.vibration_mm_s < 0:
        raise ValueError("vibration cannot be negative")
    if sample.cycle_time_s <= 0:
        raise ValueError("cycle time must be positive")
    if sample.payload_pct < 0 or sample.payload_pct > 100:
        raise ValueError("payload outside supported telemetry range")
    if sample.timestamp_s < 0:
        raise ValueError("timestamp cannot be negative")

    penalties = 0.0
    reasons: list[str] = []
    if sample.joint_temperature_c > 85:
        penalties += 0.30
        reasons.append("joint-overtemperature")
    if sample.vibration_mm_s > 6:
        penalties += 0.30
        reasons.append("excess-vibration")
    if sample.cycle_time_s > 12:
        penalties += 0.15
        reasons.append("cycle-time-drift")
    if sample.payload_pct > 90:
        penalties += 0.15
        reasons.append("high-payload")

    score = max(0.0, min(1.0, 1.0 - penalties))
    return InspectionAssessment(
        robot_id=sample.robot_id,
        health_score=score,
        maintenance_signal=score < 0.70,
        confidence=0.97 if reasons else 0.96,
        reasons=tuple(reasons),
    )


def govern_robotics(
    *,
    mode: RoboticsMode,
    assessments: Sequence[InspectionAssessment],
    telemetry_fresh: bool,
    evidence_complete: bool,
) -> RoboticsGovernanceDecision:
    evidence = ["telemetry-integrity", "inspection-verification"]
    if evidence_complete:
        evidence.append("evidence-complete")

    if not telemetry_fresh:
        return RoboticsGovernanceDecision(
            RoboticsDecision.DENY, mode, "stale robot telemetry", tuple(evidence)
        )
    if not evidence_complete:
        return RoboticsGovernanceDecision(
            RoboticsDecision.DENY,
            mode,
            "required evidence is incomplete",
            tuple(evidence),
        )
    if any(item.confidence < 0.90 for item in assessments):
        return RoboticsGovernanceDecision(
            RoboticsDecision.ESCALATE,
            mode,
            "inspection confidence requires human authority",
            tuple(evidence),
        )
    if mode in {RoboticsMode.SIMULATION, RoboticsMode.SHADOW}:
        return RoboticsGovernanceDecision(
            RoboticsDecision.ALLOW,
            mode,
            "robot inspection analysis permitted; no physical control",
            tuple(evidence),
        )
    return RoboticsGovernanceDecision(
        RoboticsDecision.ESCALATE,
        mode,
        "controlled robot operation requires explicit authority",
        tuple(evidence),
    )


def run_robotics_shadow(
    provider: RobotTelemetryProvider,
    *,
    telemetry_fresh: bool = True,
    evidence_complete: bool = True,
) -> tuple[tuple[InspectionAssessment, ...], RoboticsGovernanceDecision]:
    samples = tuple(provider.read())
    assessments = tuple(inspect_robot(sample) for sample in samples)
    decision = govern_robotics(
        mode=RoboticsMode.SHADOW,
        assessments=assessments,
        telemetry_fresh=telemetry_fresh,
        evidence_complete=evidence_complete,
    )
    return assessments, decision


__all__ = [
    "InspectionAssessment",
    "RobotTelemetry",
    "RobotTelemetryProvider",
    "RoboticsDecision",
    "RoboticsGovernanceDecision",
    "RoboticsMode",
    "SyntheticRobotTelemetryProvider",
    "govern_robotics",
    "inspect_robot",
    "run_robotics_shadow",
]
