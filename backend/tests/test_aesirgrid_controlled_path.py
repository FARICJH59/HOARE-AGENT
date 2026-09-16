"""End-to-end controlled-path validation for HOARE Case Study #1.

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


def _staged_product():
    product = build_product_definition(
        product_id="aesirgrid-predictive-maintenance",
        product_version="1.0.0",
        domain="energy",
        capabilities=("Telemetry", "PredictiveMaintenance", "AnomalyDetection"),
        domain_policies=("energy.grid.safety.v1",),
        evidence_requirements=("telemetry-integrity", "model-verification", "AEGIS-authorization"),
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


def _lease(product, **overrides):
    values = dict(
        lease_id="lease-controlled-001",
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )
    values.update(overrides)
    return AuthorityLease(**values)


def _request(product, lease):
    return ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )


def test_staged_to_authorized_requires_valid_lease():
    product = _staged_product()
    admission = admit_controlled_action(_request(product, _lease(product)))
    authorized = authorize_product(product, admission)

    assert admission.decision is AegisDecision.ALLOW
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.authority == "product-definition-only"
    assert authorized.can_execute is False


def test_expired_lease_cannot_authorize_product():
    product = _staged_product()
    admission = admit_controlled_action(
        _request(product, _lease(product, expires_at_s=150.0))
    )

    assert admission.decision is AegisDecision.DENY
    with pytest.raises(ValueError, match="ALLOW admission"):
        authorize_product(product, admission)


def test_wrong_tenant_cannot_authorize_product():
    product = _staged_product()
    admission = admit_controlled_action(
        ControlledActionRequest(
            tenant_id="tenant-attacker",
            product_id=product.product_id,
            action="apply_maintenance_setpoint",
            requested_mode=AesirGridMode.CONTROLLED,
            now_s=150.0,
            lease=_lease(product),
        )
    )

    assert admission.decision is AegisDecision.DENY
    with pytest.raises(ValueError, match="ALLOW admission"):
        authorize_product(product, admission)


def test_authorized_product_still_cannot_execute():
    product = _staged_product()
    admission = admit_controlled_action(_request(product, _lease(product)))
    authorized = authorize_product(product, admission)

    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False
