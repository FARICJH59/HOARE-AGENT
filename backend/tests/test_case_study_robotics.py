"""Formal HOARE Case Study #2: governed industrial robotics.

Provenance: 2026-09-16
"""

import pytest

from hoare_engine.product_factory import ProductLifecycle, build_product_definition
from hoare_engine.robotics_case_study import (
    RoboticsDecision,
    RoboticsMode,
    RobotTelemetry,
    assess_robot,
    govern_robotics_action,
)


def _robot_product():
    product = build_product_definition(
        product_id="industrial-robot-maintenance",
        product_version="1.0.0",
        domain="robotics",
        capabilities=("Telemetry", "PredictiveMaintenance", "SafetyMonitoring"),
        domain_policies=("robotics.machine-safety.v1",),
        workflows=("robot-telemetry", "maintenance-assessment"),
        integrations=("robot-controller-adapter",),
        deployment_profiles=("simulation", "shadow", "controlled", "live"),
        compliance_profiles=("industrial-safety",),
        evidence_requirements=("telemetry-integrity", "robot-safety-check", "model-verification"),
        vertical_ip_refs=("robotics:maintenance-models:v1",),
        customer_ip_refs=("customer:factory-a:robot-telemetry:v4",),
        metadata={"case_study": "HOARE-CS-002"},
    )
    for target in (
        ProductLifecycle.PLANNED,
        ProductLifecycle.BUILDING,
        ProductLifecycle.TESTING,
        ProductLifecycle.VERIFIED,
        ProductLifecycle.STAGED,
    ):
        product = product.transition(target)
    return product


def _nominal():
    return RobotTelemetry("robot-001", 62.0, 2.0, 70.0, True, 1000.0)


def _maintenance_signal():
    return RobotTelemetry("robot-002", 102.0, 9.0, 94.0, True, 1000.0)


def test_robotics_product_is_built_by_same_hoare_factory_contract():
    product = _robot_product()
    assert product.domain == "robotics"
    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.authority == "product-definition-only"
    assert product.can_execute is False
    assert product.metadata["case_study"] == "HOARE-CS-002"


def test_robotics_case_study_detects_maintenance_signal():
    assessment = assess_robot(_maintenance_signal())
    assert assessment.robot_id == "robot-002"
    assert assessment.maintenance_required is True
    assert assessment.health_score < 0.70
    assert "high-joint-temperature" in assessment.reason
    assert "high-vibration" in assessment.reason


def test_robotics_shadow_is_allowed_without_physical_actuation():
    assessment = assess_robot(_maintenance_signal())
    governance = govern_robotics_action(
        mode=RoboticsMode.SHADOW,
        assessment=assessment,
        evidence_complete=True,
    )
    assert governance.decision is RoboticsDecision.ALLOW
    assert "no physical actuation" in governance.reason


def test_robotics_controlled_requires_explicit_authority():
    assessment = assess_robot(_nominal())
    governance = govern_robotics_action(
        mode=RoboticsMode.CONTROLLED,
        assessment=assessment,
        evidence_complete=True,
        authority_present=False,
    )
    assert governance.decision is RoboticsDecision.ESCALATE
    assert "explicit authority" in governance.reason


def test_robotics_live_can_only_pass_governance_with_explicit_authority():
    assessment = assess_robot(_nominal())
    governance = govern_robotics_action(
        mode=RoboticsMode.LIVE,
        assessment=assessment,
        evidence_complete=True,
        authority_present=True,
    )
    assert governance.decision is RoboticsDecision.ALLOW


def test_robot_safety_zone_failure_is_denied_even_with_authority():
    unsafe = RobotTelemetry("robot-003", 60.0, 2.0, 70.0, False, 1000.0)
    assessment = assess_robot(unsafe)
    governance = govern_robotics_action(
        mode=RoboticsMode.CONTROLLED,
        assessment=assessment,
        evidence_complete=True,
        authority_present=True,
    )
    assert governance.decision is RoboticsDecision.DENY
    assert "safety zone" in governance.reason


def test_robotics_incomplete_evidence_is_denied():
    governance = govern_robotics_action(
        mode=RoboticsMode.SHADOW,
        assessment=assess_robot(_nominal()),
        evidence_complete=False,
    )
    assert governance.decision is RoboticsDecision.DENY
    assert "evidence" in governance.reason


def test_invalid_robot_telemetry_fails_closed():
    invalid = RobotTelemetry("robot-invalid", 60.0, -1.0, 70.0, True, 1000.0)
    with pytest.raises(ValueError, match="invalid telemetry range"):
        assess_robot(invalid)
