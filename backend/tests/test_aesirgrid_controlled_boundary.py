"""End-to-end controlled boundary tests for HOARE Case Study #1.

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


PRODUCT_ID = "aesirgrid-predictive-maintenance"
TENANT_ID = "tenant-grid-001"


def _staged_product():
    product = build_product_definition(
        product_id=PRODUCT_ID,
        product_version="1.0.0",
        domain="energy",
        capabilities=("Telemetry", "PredictiveMaintenance"),
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
        lease_id="lease-aesirgrid-controlled-001",
        tenant_id=TENANT_ID,
        product_id=product.product_id,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )
    values.update(overrides)
    return AuthorityLease(**values)


def _request(product, lease, **overrides):
    values = dict(
        tenant_id=TENANT_ID,
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )
    values.update(overrides)
    return ControlledActionRequest(**values)


def test_full_controlled_admission_path_requires_staged_product_and_valid_lease():
    product = _staged_product()
    lease = _lease(product)
    request = _request(product, lease)

    admission = admit_controlled_action(request)
    authorized = authorize_product(product, admission)

    assert admission.decision is AegisDecision.ALLOW
    assert admission.lease_id == lease.lease_id
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.authority == "product-definition-only"
    assert authorized.can_execute is False


def test_controlled_request_without_lease_escalates_and_cannot_authorize_product():
    product = _staged_product()
    admission = admit_controlled_action(_request(product, None))

    assert admission.decision is AegisDecision.ESCALATE
    with pytest.raises(ValueError, match="ALLOW admission"):
        authorize_product(product, admission)
    assert product.lifecycle_state is ProductLifecycle.STAGED


def test_wrong_tenant_cannot_use_valid_lease():
    product = _staged_product()
    admission = admit_controlled_action(
        _request(product, _lease(product), tenant_id="tenant-attacker")
    )

    assert admission.decision is AegisDecision.DENY
    assert "tenant mismatch" in admission.reason


def test_expired_lease_cannot_authorize_product():
    product = _staged_product()
    lease = _lease(product, expires_at_s=150.0)
    admission = admit_controlled_action(_request(product, lease))

    assert admission.decision is AegisDecision.DENY
    with pytest.raises(ValueError, match="ALLOW admission"):
        authorize_product(product, admission)


def test_live_mode_requires_live_authority_lease():
    product = _staged_product()
    controlled_lease = _lease(product)
    admission = admit_controlled_action(
        _request(
            product,
            controlled_lease,
            requested_mode=AesirGridMode.LIVE,
        )
    )

    assert admission.decision is AegisDecision.DENY
    assert "mode mismatch" in admission.reason
