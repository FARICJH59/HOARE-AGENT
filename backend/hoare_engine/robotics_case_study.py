"""Provider-neutral industrial robotics case-study validation.

Provenance: 2026-09-17

The module is deterministic and synthetic. It validates perception/telemetry
and safety-interlock evidence without issuing physical robot commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from hoare_engine.aesirgrid_case_study import AegisDecision


class RoboticsMode(str, Enum):
    SIMULATION = "SIMULATION"
    SHADOW = "SHADOW"
    CONTROLLED = "CONTROLLED"
    LIVE = "LIVE"


@dataclass(frozen=True)
class RobotTelemetry:
    robot_id: str
    joint_temperature_c: float
    vibration_mm_s: float
    payload_pct: float
    cycle_time_s: float
    safety_interlock_engaged: bool
    timestamp_s: float


@dataclass(frozen=True)
class RobotAssessment:
    robot_id: str
    health_score: float
    anomaly: bool
    confidence: float
    reason: str


@dataclass(frozen=True)
class RoboticsGovernanceDecision:
    decision: AegisDecision
    mode: RoboticsMode
    reason: str
    evidence: tuple[str, ...]


class SyntheticRobotTelemetryProvider:
    def __init__(self, samples: Sequence[RobotTelemetry]) -> None:
        self._samples = tuple(samples)

    def read(self) -> tuple[RobotTelemetry, ...]:
        return self._samples


def assess_robot(sample: RobotTelemetry) -> RobotAssessment:
    if not sample.robot_id.strip():
        raise ValueError("robot_id is required")
    if not 0 <= sample.payload_pct <= 100:
        raise ValueError("payload outside supported telemetry range")
    if sample.joint_temperature_c < -40 or sample.joint_temperature_c > 180:
        raise ValueError("joint temperature outside supported telemetry range")
    if sample.vibration_mm_s < 0 or sample.cycle_time_s <= 0 or sample.timestamp_s < 0:
        raise ValueError("invalid robot telemetry range")

    penalties = 0.0
    reasons: list[str] = []
    if sample.joint_temperature_c > 85:
        penalties += 0.30
        reasons.append("high-joint-temperature")
    if sample.vibration_mm_s > 6:
        penalties += 0.30
        reasons.append("high-vibration")
    if sample.payload_pct > 90:
        penalties += 0.20
        reasons.append("high-payload")
    if sample.safety_interlock_engaged is False:
        penalties += 0.50
        reasons.append("safety-interlock-open")

    score = max(0.0, min(1.0, 1.0 - penalties))
    anomaly = score < 0.70
    confidence = 0.98 if anomaly else 0.95
    return RobotAssessment(
        robot_id=sample.robot_id,
        health_score=score,
        anomaly=anomaly,
        confidence=confidence,
        reason=",".join(reasons) if reasons else "nominal",
    )


def evaluate_robotics_governance(
    *,
    mode: RoboticsMode,
    assessments: Sequence[RobotAssessment],
    telemetry_fresh: bool = True,
    evidence_complete: bool = True,
) -> RoboticsGovernanceDecision:
    evidence = ["sensor-integrity", "model-verification", "safety-interlock-state"]
    if evidence_complete:
        evidence.append("evidence-complete")

    if not telemetry_fresh:
        return RoboticsGovernanceDecision(AegisDecision.DENY, mode, "stale telemetry", tuple(evidence))
    if not evidence_complete:
        return RoboticsGovernanceDecision(AegisDecision.DENY, mode, "required evidence is incomplete", tuple(evidence))
    if any(item.confidence < 0.90 for item in assessments):
        return RoboticsGovernanceDecision(
            AegisDecision.ESCALATE,
            mode,
            "model confidence requires human authority",
            tuple(evidence),
        )
    if any("safety-interlock-open" in item.reason for item in assessments):
        return RoboticsGovernanceDecision(
            AegisDecision.DENY,
            mode,
            "safety interlock is not engaged",
            tuple(evidence),
        )
    if mode in {RoboticsMode.SIMULATION, RoboticsMode.SHADOW}:
        return RoboticsGovernanceDecision(
            AegisDecision.ALLOW,
            mode,
            "robotics analysis permitted; no physical motion",
            tuple(evidence),
        )
    return RoboticsGovernanceDecision(
        AegisDecision.ESCALATE,
        mode,
        "controlled/live robot operation requires explicit authority",
        tuple(evidence),
    )


__all__ = [
    "RobotAssessment",
    "RobotTelemetry",
    "RoboticsGovernanceDecision",
    "RoboticsMode",
    "SyntheticRobotTelemetryProvider",
    "assess_robot",
    "evaluate_robotics_governance",
]
