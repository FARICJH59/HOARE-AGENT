"""HOARE Case Study #2: governed industrial robotics product.

Provenance: 2026-09-17

This deliberately uses the same product-factory contract as Case Study #1
while changing the vertical from energy to robotics. It validates that the
HOARE control-plane abstraction is not encoded around AesirGrid.
"""

import pytest

from hoare_engine.product_factory import ProductFactoryError, ProductLifecycle, build_product_definition


ROBOTICS_INTENT = (
    "Build a governed industrial-robot inspection and predictive-maintenance "
    "system for a manufacturing cell."
)


def _build_robotics_product():
    return build_product_definition(
        product_id="industrial-robot-inspection",
        product_version="1.0.0",
        domain="robotics",
        capabilities=("MachineVision", "RobotTelemetry", "AnomalyDetection", "PredictiveMaintenance"),
        domain_policies=("robotics.cell.safety.v1",),
        workflows=("robot-inspection", "maintenance-assessment"),
        integrations=("robot-controller-readonly",),
        deployment_profiles=("simulation", "shadow", "controlled", "live"),
        compliance_profiles=("ISO-10218", "NIST-AI-RMF"),
        evidence_requirements=("sensor-integrity", "model-verification", "safety-interlock-state", "AEGIS-authorization"),
        vertical_ip_refs=("robotics:inspection-models:v1",),
        customer_ip_refs=("customer:factory-cell:telemetry:v1",),
        metadata={"intent": ROBOTICS_INTENT, "case_study": "HOARE-CS-002"},
    )


def test_robotics_uses_same_universal_product_factory_contract():
    product = _build_robotics_product()
    for target in (ProductLifecycle.PLANNED, ProductLifecycle.BUILDING, ProductLifecycle.TESTING, ProductLifecycle.VERIFIED, ProductLifecycle.STAGED):
        product = product.transition(target)

    assert product.product_id == "industrial-robot-inspection"
    assert product.domain == "robotics"
    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.owner == "Tech Fusion AI ML LLC"
    assert product.authority == "product-definition-only"
    assert product.can_execute is False
    assert product.metadata["case_study"] == "HOARE-CS-002"


def test_robotics_has_no_energy_specific_requirements():
    product = _build_robotics_product()
    assert product.domain_policies == ("robotics.cell.safety.v1",)
    assert product.integrations == ("robot-controller-readonly",)
    assert "energy.grid.safety.v1" not in product.domain_policies


def test_robotics_keeps_vertical_and_customer_ip_separate():
    product = _build_robotics_product()
    assert product.vertical_ip_refs == ("robotics:inspection-models:v1",)
    assert product.customer_ip_refs == ("customer:factory-cell:telemetry:v1",)
    assert set(product.vertical_ip_refs).isdisjoint(product.customer_ip_refs)


def test_robotics_cannot_bypass_authorization_boundary():
    product = _build_robotics_product()
    for target in (ProductLifecycle.PLANNED, ProductLifecycle.BUILDING, ProductLifecycle.TESTING, ProductLifecycle.VERIFIED, ProductLifecycle.STAGED):
        product = product.transition(target)

    with pytest.raises(ProductFactoryError, match="invalid lifecycle transition"):
        product.transition(ProductLifecycle.DEPLOYED)
