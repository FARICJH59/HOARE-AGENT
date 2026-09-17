"""HOARE Case Study #2 tests: industrial robotics inspection.

Provenance: 2026-09-16
"""

import pytest

from hoare_engine.product_factory import ProductLifecycle, build_product_definition
from hoare_engine.robotics_case_study import (
    RobotTelemetry,
    RoboticsDecision,
    RoboticsMode,
    SyntheticRobotTelemetryProvider,
    govern_robotics,
    inspect_robot,
    run_robotics_shadow,
)


def _robot_product():
    product = build_product_definition(
        product_id="industrial-robot-inspection",
        product_version="1.0.0",
        domain="robotics",
        capabilities=("RobotTelemetry", "PredictiveMaintenance", "AnomalyDetection"),
        domain_policies=("robotics.machine-safety.v1",),
        workflows=("robot-telemetry", "robot-health-assessment"),
        integrations=("robot-controller-adapter",),
        deployment_profiles=("simulation", "shadow", "controlled"),
        compliance_profiles=("ISO-10218",),
        evidence_requirements=("telemetry-integrity", "inspection-verification"),
        vertical_ip_refs=("robotics:inspection-models:v1",),
        customer_ip_refs=("customer:factory:robot-telemetry:v1",),
        metadata={"case_study": "HOARE-CS-002"},
    )
    for state in (
        ProductLifecycle.PLANNED,
        ProductLifecycle.BUILDING,
        ProductLifecycle.TESTING,
        ProductLifecycle.VERIFIED,
        ProductLifecycle.STAGED,
    ):
        product = product.transition(state)
    return product


def _nominal_robot():
    return RobotTelemetry("robot-001", 62.0, 2.0, 9.5, 65.0, 1000.0)


def _degraded_robot():
    return RobotTelemetry("robot-002", 101.0, 9.0, 15.0, 96.0, 1000.0)


def test_case_study_uses_same_product_factory_for_a_different_vertical():
    product = _robot_product()

    assert product.domain == "robotics"
    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.authority == "product-definition-only"
    assert product.can_execute is False
    assert product.metadata["case_study"] == "HOARE-CS-002"
    assert product.vertical_ip_refs == ("robotics:inspection-models:v1",)
    assert product.customer_ip_refs == ("customer:factory:robot-telemetry:v1",)


def test_robot_inspection_detects_degraded_asset():
    assessment = inspect_robot(_degraded_robot())

    assert assessment.maintenance_signal is True
    assert assessment.health_score < 0.70
    assert "joint-overtemperature" in assessment.reasons
    assert "excess-vibration" in assessment.reasons
    assert "cycle-time-drift" in assessment.reasons


def test_robotics_shadow_allows_analysis_without_physical_control():
    provider = SyntheticRobotTelemetryProvider([_nominal_robot(), _degraded_robot()])

    assessments, decision = run_robotics_shadow(provider)

    assert len(assessments) == 2
    assert decision.decision is RoboticsDecision.ALLOW
    assert decision.mode is RoboticsMode.SHADOW
    assert "no physical control" in decision.reason
    assert "telemetry-integrity" in decision.evidence
    assert "inspection-verification" in decision.evidence


def test_robotics_stale_telemetry_is_denied():
    assessment = inspect_robot(_nominal_robot())
    decision = govern_robotics(
        mode=RoboticsMode.SHADOW,
        assessments=(assessment,),
        telemetry_fresh=False,
        evidence_complete=True,
    )

    assert decision.decision is RoboticsDecision.DENY


def test_robotics_controlled_mode_requires_explicit_authority():
    assessment = inspect_robot(_nominal_robot())
    decision = govern_robotics(
        mode=RoboticsMode.CONTROLLED,
        assessments=(assessment,),
        telemetry_fresh=True,
        evidence_complete=True,
    )

    assert decision.decision is RoboticsDecision.ESCALATE
    assert "explicit authority" in decision.reason


def test_invalid_robot_telemetry_fails_closed():
    invalid = RobotTelemetry("robot-invalid", 60.0, -1.0, 9.0, 50.0, 1000.0)

    with pytest.raises(ValueError, match="vibration cannot be negative"):
        inspect_robot(invalid)
