"""HOARE Case Study #2: governed industrial robotics.

Provenance: 2026-09-16

This non-energy case study validates that HOARE's product-factory and
execution-governance boundaries can compose a robotics solution without
introducing an AesirGrid-specific core.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RoboticsDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


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
    safety_zone_clear: bool
    timestamp_s: float


@dataclass(frozen=True)
class RobotAssessment:
    robot_id: str
    health_score: float
    maintenance_required: bool
    safety_clear: bool
    reason: str


@dataclass(frozen=True)
class RoboticsGovernance:
    decision: RoboticsDecision
    mode: RoboticsMode
    reason: str
    evidence: tuple[str, ...]


def assess_robot(sample: RobotTelemetry) -> RobotAssessment:
    """Produce a deterministic predictive-maintenance assessment."""
    if not sample.robot_id.strip():
        raise ValueError("robot_id is required")
    if not 0 <= sample.payload_pct <= 100:
        raise ValueError("payload outside supported telemetry range")
    if sample.joint_temperature_c < -20 or sample.joint_temperature_c > 140:
        raise ValueError("joint temperature outside supported telemetry range")
    if sample.vibration_mm_s < 0 or sample.timestamp_s < 0:
        raise ValueError("invalid telemetry range")

    penalty = 0.0
    reasons: list[str] = []
    if sample.joint_temperature_c > 85:
        penalty += 0.30
        reasons.append("high-joint-temperature")
    if sample.vibration_mm_s > 6:
        penalty += 0.30
        reasons.append("high-vibration")
    if sample.payload_pct > 90:
        penalty += 0.15
        reasons.append("high-payload")

    score = max(0.0, min(1.0, 1.0 - penalty))
    return RobotAssessment(
        robot_id=sample.robot_id,
        health_score=score,
        maintenance_required=score < 0.70,
        safety_clear=sample.safety_zone_clear,
        reason=",".join(reasons) if reasons else "nominal",
    )


def govern_robotics_action(
    *,
    mode: RoboticsMode,
    assessment: RobotAssessment,
    evidence_complete: bool,
    authority_present: bool = False,
) -> RoboticsGovernance:
    """Apply a safety-first governance boundary before robot control."""
    evidence = ("telemetry-integrity", "robot-safety-check")
    if evidence_complete:
        evidence += ("model-verification",)
    if not evidence_complete:
        return RoboticsGovernance(
            RoboticsDecision.DENY, mode, "required evidence is incomplete", evidence
        )
    if not assessment.safety_clear:
        return RoboticsGovernance(
            RoboticsDecision.DENY, mode, "robot safety zone is not clear", evidence
        )
    if mode in {RoboticsMode.SIMULATION, RoboticsMode.SHADOW}:
        return RoboticsGovernance(
            RoboticsDecision.ALLOW,
            mode,
            "robotics analysis permitted; no physical actuation",
            evidence,
        )
    if not authority_present:
        return RoboticsGovernance(
            RoboticsDecision.ESCALATE,
            mode,
            "explicit authority required for physical actuation",
            evidence,
        )
    return RoboticsGovernance(
        RoboticsDecision.ALLOW,
        mode,
        "explicit authority permits governed physical actuation",
        evidence,
    )


__all__ = [
    "RobotTelemetry",
    "RobotAssessment",
    "RoboticsDecision",
    "RoboticsGovernance",
    "RoboticsMode",
    "assess_robot",
    "govern_robotics_action",
]
