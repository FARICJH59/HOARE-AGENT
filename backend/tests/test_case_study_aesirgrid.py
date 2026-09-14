"""Formal HOARE Case Study #1: AesirGrid predictive maintenance.

Provenance: 2026-09-12
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


def _aesirgrid_case_study():
    intent = (
        "Build an energy-grid predictive-maintenance system for AesirGrid "
        "using telemetry from grid assets."
    )
    product = build_product_definition(
        product_id="aesirgrid-predictive-maintenance",
        product_version="1.0.0",
        domain="energy",
        capabilities=(
            "Telemetry",
            "PredictiveMaintenance",
            "AssetHealthScoring",
            "AnomalyDetection",
        ),
        domain_policies=("energy.grid.safety.v1",),
        workflows=("telemetry-ingestion", "asset-health-assessment"),
        integrations=("grid-telemetry",),
        deployment_profiles=("simulation", "shadow", "controlled", "live"),
        compliance_profiles=("NIST-AI-RMF",),
        evidence_requirements=(
            "telemetry-integrity",
            "model-verification",
            "AEGIS-authorization",
        ),
        vertical_ip_refs=("aesirgrid:grid-models:v1",),
        customer_ip_refs=("customer:grid-operator:telemetry:v1",),
        metadata={"intent": intent, "case_study": "HOARE-CS-001"},
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


def _controlled_request(product, lease=None):
    return ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )


def _valid_lease(product):
    return AuthorityLease(
        lease_id="lease-aesirgrid-001",
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )


def test_aesirgrid_case_study_completes_governed_build_to_staged():
    intent, product = _aesirgrid_case_study()
    assert intent.startswith("Build an energy-grid predictive-maintenance system")
    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.authority == "product-definition-only"
    assert product.can_execute is False
    assert product.capabilities == (
        "Telemetry",
        "PredictiveMaintenance",
        "AssetHealthScoring",
        "AnomalyDetection",
    )
    assert product.domain_policies == ("energy.grid.safety.v1",)
    assert product.evidence_requirements == (
        "telemetry-integrity",
        "model-verification",
        "AEGIS-authorization",
    )
    assert product.vertical_ip_refs == ("aesirgrid:grid-models:v1",)
    assert product.customer_ip_refs == ("customer:grid-operator:telemetry:v1",)


def test_aesirgrid_case_study_cannot_skip_staged_authorization_boundary():
    _, product = _aesirgrid_case_study()

    with pytest.raises(ValueError, match="invalid lifecycle transition"):
        product.transition(ProductLifecycle.DEPLOYED)


def test_aesirgrid_case_study_authorizes_only_with_valid_controlled_lease():
    _, product = _aesirgrid_case_study()
    admission = admit_controlled_action(
        _controlled_request(product, _valid_lease(product))
    )

    authorized = authorize_product(product, admission)

    assert admission.decision is AegisDecision.ALLOW
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False


def test_aesirgrid_case_study_authorization_does_not_create_execution_authority():
    _, product = _aesirgrid_case_study()
    admission = admit_controlled_action(
        _controlled_request(product, _valid_lease(product))
    )
    authorized = authorize_product(product, admission)

    assert authorized.authority == "product-definition-only"
    assert authorized.can_execute is False


def test_aesirgrid_case_study_denies_authorization_without_valid_lease():
    _, product = _aesirgrid_case_study()
    admission = admit_controlled_action(_controlled_request(product))

    assert admission.decision is AegisDecision.ESCALATE
    with pytest.raises(ValueError, match="ALLOW admission"):
        authorize_product(product, admission)
