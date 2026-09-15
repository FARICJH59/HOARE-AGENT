"""End-to-end control-plane handoff test for HOARE Case Study #1.

Provenance: 2026-09-15

This test deliberately stops before physical execution. It proves that a
verified/staged product can cross into AUTHORIZED only through an explicit
lease and that the resulting authorization still does not grant the product
execution authority.
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


def _staged_product():
    product = build_product_definition(
        product_id="aesirgrid-predictive-maintenance",
        product_version="1.0.0",
        domain="energy",
        capabilities=("Telemetry", "PredictiveMaintenance", "AssetHealthScoring"),
        domain_policies=("energy.grid.safety.v1",),
        workflows=("telemetry-ingestion", "asset-health-assessment"),
        integrations=("grid-telemetry",),
        deployment_profiles=("simulation", "shadow", "controlled", "live"),
        compliance_profiles=("NIST-AI-RMF",),
        evidence_requirements=("telemetry-integrity", "model-verification", "AEGIS-authorization"),
        vertical_ip_refs=("aesirgrid:grid-models:v1",),
        customer_ip_refs=("customer:grid-operator:telemetry:v1",),
        metadata={"case_study": "HOARE-CS-001"},
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


def _lease(product):
    return AuthorityLease(
        lease_id="lease-aesirgrid-001",
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )


def test_case_study_controlled_handoff_crosses_only_explicit_authority_boundary():
    product = _staged_product()
    lease = _lease(product)

    request = ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )

    admission = admit_controlled_action(request)
    authorized = authorize_product(product, admission)

    assert admission.decision is AegisDecision.ALLOW
    assert admission.lease_id == lease.lease_id
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.authority == "product-definition-only"
    assert authorized.can_execute is False


def test_case_study_controlled_handoff_fails_closed_for_expired_authority():
    product = _staged_product()
    request = ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=200.0,
        lease=_lease(product),
    )

    admission = admit_controlled_action(request)

    assert admission.decision is AegisDecision.DENY
    with pytest.raises(ValueError, match="ALLOW admission"):
        authorize_product(product, admission)


def test_case_study_live_handoff_still_requires_live_specific_authority():
    product = _staged_product()
    controlled_lease = _lease(product)
    request = ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.LIVE,
        now_s=150.0,
        lease=controlled_lease,
    )

    admission = admit_controlled_action(request)

    assert admission.decision is AegisDecision.DENY
    assert "mode mismatch" in admission.reason
