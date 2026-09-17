"""Formal HOARE Case Study #2: governed industrial robotics.

Provenance: 2026-09-16
"""

import pytest

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    AuthorityStatus,
    ControlledActionRequest,
    admit_controlled_action,
    authorize_product,
)
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode
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
        product_id="industrial-robot-inspection",
        product_version="1.0.0",
        domain="robotics",
        capabilities=("MachineVision", "RobotStateMonitoring", "AnomalyDetection", "PredictiveMaintenance"),
        domain_policies=("robotics.safety.v1",),
        workflows=("robot-telemetry", "inspection-assessment"),
        integrations=("robot-controller-adapter",),
        deployment_profiles=("simulation", "shadow", "controlled", "live"),
        compliance_profiles=("industrial-safety",),
        evidence_requirements=("sensor-integrity", "model-verification", "safety-authorization"),
        vertical_ip_refs=("robotics:inspection-models:v1",),
        customer_ip_refs=("customer:factory:robot-telemetry:v1",),
        metadata={"case_study": "HOARE-CS-002"},
    )
    for target in (ProductLifecycle.PLANNED, ProductLifecycle.BUILDING, ProductLifecycle.TESTING, ProductLifecycle.VERIFIED, ProductLifecycle.STAGED):
        product = product.transition(target)
    return product


def _nominal():
    return RobotTelemetry("robot-001", 62.0, 2.0, 70.0, True, 1000.0)


def _maintenance_signal():
    return RobotTelemetry("robot-002", 102.0, 9.0, 94.0, True, 1000.0)


def _lease(product):
    return AuthorityLease(
        lease_id="lease-robotics-001",
        tenant_id="tenant-factory-001",
        product_id=product.product_id,
        action="start_inspection_cycle",
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
        authority_source="factory-operator-approval",
        evidence_refs=("sensor-integrity", "model-verification"),
        scope=("start_inspection_cycle",),
        audit_correlation_id="audit-robotics-001",
    )


def test_robotics_reuses_hoare_factory_contract():
    product = _robot_product()
    assert product.domain == "robotics"
    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.authority == "product-definition-only"
    assert product.can_execute is False
    assert product.metadata["case_study"] == "HOARE-CS-002"


def test_robotics_detects_maintenance_signal():
    assessment = assess_robot(_maintenance_signal())
    assert assessment.maintenance_required is True
    assert assessment.health_score < 0.70


def test_robotics_shadow_allows_analysis_without_actuation():
    governance = govern_robotics_action(mode=RoboticsMode.SHADOW, assessment=assess_robot(_nominal()), evidence_complete=True)
    assert governance.decision is RoboticsDecision.ALLOW
    assert "no physical actuation" in governance.reason


def test_robotics_controlled_requires_explicit_authority():
    governance = govern_robotics_action(mode=RoboticsMode.CONTROLLED, assessment=assess_robot(_nominal()), evidence_complete=True)
    assert governance.decision is RoboticsDecision.ESCALATE


def test_robotics_live_with_authority_is_governance_allowed():
    governance = govern_robotics_action(mode=RoboticsMode.LIVE, assessment=assess_robot(_nominal()), evidence_complete=True, authority_present=True)
    assert governance.decision is RoboticsDecision.ALLOW


def test_unsafe_robot_is_denied_even_with_authority():
    unsafe = RobotTelemetry("robot-003", 60.0, 2.0, 70.0, False, 1000.0)
    governance = govern_robotics_action(mode=RoboticsMode.CONTROLLED, assessment=assess_robot(unsafe), evidence_complete=True, authority_present=True)
    assert governance.decision is RoboticsDecision.DENY
    assert "safety zone" in governance.reason


def test_incomplete_evidence_is_denied():
    governance = govern_robotics_action(mode=RoboticsMode.SHADOW, assessment=assess_robot(_nominal()), evidence_complete=False)
    assert governance.decision is RoboticsDecision.DENY


def test_invalid_robot_telemetry_fails_closed():
    with pytest.raises(ValueError, match="invalid telemetry range"):
        assess_robot(RobotTelemetry("robot-invalid", 60.0, -1.0, 70.0, True, 1000.0))


def test_robotics_authority_is_bound_to_exact_product_and_action():
    product = _robot_product()
    request = ControlledActionRequest(
        tenant_id="tenant-factory-001",
        product_id=product.product_id,
        action="start_inspection_cycle",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=_lease(product),
    )
    admission = admit_controlled_action(request)
    assert admission.decision is AegisDecision.ALLOW
    authorized = authorize_product(product, admission)
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED


def test_robotics_wrong_tenant_is_denied_before_authorization():
    product = _robot_product()
    request = ControlledActionRequest(
        tenant_id="attacker-tenant",
        product_id=product.product_id,
        action="start_inspection_cycle",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=_lease(product),
    )
    admission = admit_controlled_action(request)
    assert admission.decision is AegisDecision.DENY
    with pytest.raises(ValueError, match="ALLOW admission"):
        authorize_product(product, admission)
