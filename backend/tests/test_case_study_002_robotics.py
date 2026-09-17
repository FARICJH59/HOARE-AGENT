"""Formal HOARE Case Study #2: governed industrial robotics inspection.

Provenance: 2026-09-16
Case study ID: HOARE-CS-002

This deliberately uses a different vertical from AesirGrid while reusing the
same HOARE product-factory contracts. The synthetic robot telemetry is an
inspection workload only; this case study does not issue motion commands.
"""

from dataclasses import dataclass

import pytest

from hoare_engine.product_factory import ProductLifecycle, build_product_definition


@dataclass(frozen=True)
class RobotObservation:
    robot_id: str
    joint_temperature_c: float
    vibration_mm_s: float
    inspection_confidence: float


def assess_robot_observation(observation: RobotObservation) -> tuple[bool, str]:
    if not observation.robot_id.strip():
        raise ValueError("robot_id is required")
    if observation.joint_temperature_c < -20 or observation.joint_temperature_c > 130:
        raise ValueError("joint temperature outside supported range")
    if observation.vibration_mm_s < 0:
        raise ValueError("vibration cannot be negative")
    if not 0 <= observation.inspection_confidence <= 1:
        raise ValueError("inspection confidence must be between 0 and 1")

    degraded = (
        observation.joint_temperature_c > 85
        or observation.vibration_mm_s > 6
        or observation.inspection_confidence < 0.90
    )
    return degraded, "inspection-degradation" if degraded else "nominal"


def _robotics_product():
    intent = (
        "Build a governed industrial-robot inspection and predictive-maintenance "
        "system using robot telemetry and inspection observations."
    )
    product = build_product_definition(
        product_id="industrial-robot-inspection",
        product_version="1.0.0",
        domain="robotics",
        capabilities=(
            "RobotTelemetry",
            "InspectionAnalysis",
            "PredictiveMaintenance",
            "AssetHealthScoring",
        ),
        domain_policies=("robotics.safety.inspection.v1",),
        workflows=("robot-telemetry-ingestion", "inspection-assessment"),
        integrations=("robot-telemetry",),
        deployment_profiles=("simulation", "shadow", "controlled", "live"),
        compliance_profiles=("industrial-safety",),
        evidence_requirements=(
            "telemetry-integrity",
            "inspection-verification",
            "AEGIS-authorization",
        ),
        vertical_ip_refs=("robotics:inspection-models:v1",),
        customer_ip_refs=("customer:factory:robot-telemetry:v1",),
        metadata={"intent": intent, "case_study": "HOARE-CS-002"},
    )
    for target in (
        ProductLifecycle.PLANNED,
        ProductLifecycle.BUILDING,
        ProductLifecycle.TESTING,
        ProductLifecycle.VERIFIED,
        ProductLifecycle.STAGED,
    ):
        product = product.transition(target)
    return intent, product


def test_robotics_case_study_reuses_hoare_product_factory_for_new_vertical():
    intent, product = _robotics_product()

    assert intent.startswith("Build a governed industrial-robot")
    assert product.product_id == "industrial-robot-inspection"
    assert product.domain == "robotics"
    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.authority == "product-definition-only"
    assert product.can_execute is False
    assert "RobotTelemetry" in product.capabilities
    assert "InspectionAnalysis" in product.capabilities
    assert product.domain_policies == ("robotics.safety.inspection.v1",)
    assert product.metadata["case_study"] == "HOARE-CS-002"


def test_robotics_case_study_processes_observations_without_motion_control():
    nominal = RobotObservation("robot-001", 61.0, 2.2, 0.97)
    degraded = RobotObservation("robot-002", 94.0, 8.1, 0.96)

    nominal_result = assess_robot_observation(nominal)
    degraded_result = assess_robot_observation(degraded)

    assert nominal_result == (False, "nominal")
    assert degraded_result == (True, "inspection-degradation")


def test_robotics_case_study_preserves_ip_boundary():
    _, product = _robotics_product()

    assert product.vertical_ip_refs == ("robotics:inspection-models:v1",)
    assert product.customer_ip_refs == ("customer:factory:robot-telemetry:v1",)
    assert set(product.vertical_ip_refs).isdisjoint(product.customer_ip_refs)


def test_robotics_case_study_invalid_observation_fails_closed():
    observation = RobotObservation("robot-invalid", -30.0, 1.0, 0.95)

    with pytest.raises(ValueError, match="joint temperature"):
        assess_robot_observation(observation)


def test_robotics_case_study_cannot_skip_authorization_boundary():
    _, product = _robotics_product()

    with pytest.raises(ValueError, match="invalid lifecycle transition"):
        product.transition(ProductLifecycle.DEPLOYED)
