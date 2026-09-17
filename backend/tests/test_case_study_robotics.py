"""Formal HOARE Case Study #2: governed industrial robotics.

Provenance: 2026-09-16

This case study deliberately reuses the same HOARE product-factory and
admission contracts as Case Study #1 while changing the vertical entirely.
It demonstrates that the control-plane contract is not intrinsically tied to
energy systems.
"""

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    AuthorityStatus,
    ControlledActionRequest,
    admit_controlled_action,
    authorize_product,
)
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode
from hoare_engine.product_factory import ProductLifecycle, build_product_definition


def _robotics_product():
    product = build_product_definition(
        product_id="industrial-robot-inspection",
        product_version="1.0.0",
        domain="robotics",
        capabilities=(
            "MachineVision",
            "RobotStateMonitoring",
            "AnomalyDetection",
            "PredictiveMaintenance",
        ),
        domain_policies=("robotics.safety.v1",),
        workflows=("robot-telemetry", "inspection-assessment"),
        integrations=("robot-controller-adapter",),
        deployment_profiles=("simulation", "shadow", "controlled", "live"),
        compliance_profiles=("industrial-safety",),
        evidence_requirements=(
            "sensor-integrity",
            "model-verification",
            "safety-authorization",
        ),
        vertical_ip_refs=("robotics:inspection-models:v1",),
        customer_ip_refs=("customer:factory:robot-telemetry:v1",),
        metadata={
            "case_study": "HOARE-CS-002",
            "intent": "Build a governed robotic inspection and predictive-maintenance system.",
        },
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


def _robotics_lease(**overrides):
    values = dict(
        lease_id="lease-robotics-001",
        tenant_id="tenant-factory-001",
        product_id="industrial-robot-inspection",
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
    values.update(overrides)
    return AuthorityLease(**values)


def _robotics_request(**overrides):
    values = dict(
        tenant_id="tenant-factory-001",
        product_id="industrial-robot-inspection",
        action="start_inspection_cycle",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=_robotics_lease(),
    )
    values.update(overrides)
    return ControlledActionRequest(**values)


def test_robotics_case_study_reuses_hoare_product_factory_contract():
    product = _robotics_product()

    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.product_id == "industrial-robot-inspection"
    assert product.domain == "robotics"
    assert product.authority == "product-definition-only"
    assert product.can_execute is False
    assert "MachineVision" in product.capabilities
    assert "PredictiveMaintenance" in product.capabilities
    assert product.domain_policies == ("robotics.safety.v1",)
    assert product.compliance_profiles == ("industrial-safety",)
    assert product.metadata["case_study"] == "HOARE-CS-002"


def test_robotics_case_study_requires_governed_authority_for_controlled_action():
    product = _robotics_product()
    admission = admit_controlled_action(_robotics_request())

    assert admission.decision is AegisDecision.ALLOW
    authorized = authorize_product(product, admission)
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False


def test_robotics_case_study_denies_cross_tenant_control():
    admission = admit_controlled_action(
        _robotics_request(tenant_id="different-tenant")
    )

    assert admission.decision is AegisDecision.DENY
    assert "tenant mismatch" in admission.reason


def test_robotics_case_study_denies_action_outside_scope():
    admission = admit_controlled_action(
        _robotics_request(
            action="move_robot_to_production_cell",
            lease=_robotics_lease(scope=("start_inspection_cycle",)),
        )
    )

    assert admission.decision is AegisDecision.DENY
    assert "action mismatch" in admission.reason


def test_robotics_case_study_denies_expired_authority():
    admission = admit_controlled_action(_robotics_request(now_s=200.0))

    assert admission.decision is AegisDecision.DENY
    assert "expired" in admission.reason
