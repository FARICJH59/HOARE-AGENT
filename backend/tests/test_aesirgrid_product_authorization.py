"""Tests for the explicit STAGED -> AUTHORIZED boundary.

Provenance: 2026-09-16
"""

import pytest

from hoare_engine.aesirgrid_authority import ControlledAdmission, authorize_product
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode
from hoare_engine.product_factory import ProductLifecycle, build_product_definition


def _staged_product(product_id="aesirgrid-predictive-maintenance"):
    product = build_product_definition(
        product_id=product_id,
        product_version="1.0.0",
        domain="energy",
        capabilities=("Telemetry", "PredictiveMaintenance"),
        evidence_requirements=("telemetry-integrity", "model-verification", "AEGIS-authorization"),
        deployment_profiles=("simulation", "shadow", "controlled", "live"),
        vertical_ip_refs=("aesirgrid:grid-models:v1",),
        customer_ip_refs=("customer:grid-operator:telemetry:v1",),
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


def _allow_for(product_id):
    return ControlledAdmission(
        decision=AegisDecision.ALLOW,
        reason="authorized for controlled operation",
        lease_id="lease-aesirgrid-001",
        tenant_id="tenant-grid-001",
        product_id=product_id,
        action="apply_maintenance_setpoint",
        mode=AesirGridMode.CONTROLLED,
    )


def test_allow_admission_authorizes_matching_staged_product():
    product = _staged_product()

    authorized = authorize_product(product, _allow_for(product.product_id))

    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False


def test_allow_admission_for_different_product_cannot_authorize_product():
    product = _staged_product()

    with pytest.raises(ValueError, match="does not match"):
        authorize_product(product, _allow_for("different-product"))


def test_unbound_allow_admission_cannot_authorize_product():
    product = _staged_product()
    admission = ControlledAdmission(
        decision=AegisDecision.ALLOW,
        reason="authorized",
        lease_id="lease-aesirgrid-001",
    )

    with pytest.raises(ValueError, match="does not match"):
        authorize_product(product, admission)


def test_escalation_cannot_authorize_staged_product():
    product = _staged_product()
    admission = ControlledAdmission(
        decision=AegisDecision.ESCALATE,
        reason="explicit authority lease required",
    )

    with pytest.raises(ValueError, match="requires an ALLOW"):
        authorize_product(product, admission)


def test_deny_cannot_authorize_staged_product():
    product = _staged_product()
    admission = ControlledAdmission(
        decision=AegisDecision.DENY,
        reason="authority lease expired",
    )

    with pytest.raises(ValueError, match="requires an ALLOW"):
        authorize_product(product, admission)


def test_non_staged_product_cannot_be_authorized():
    product = build_product_definition(
        product_id="aesirgrid-predictive-maintenance",
        product_version="1.0.0",
        domain="energy",
    )

    with pytest.raises(ValueError, match="must be STAGED"):
        authorize_product(product, _allow_for(product.product_id))
