"""Case-study validation for explicit STAGED -> AUTHORIZED admission.

Provenance: 2026-09-14
"""

import pytest

from hoare_engine.aesirgrid_authority import (
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
        capabilities=("Telemetry", "PredictiveMaintenance"),
        domain_policies=("energy.grid.safety.v1",),
        evidence_requirements=("telemetry-integrity", "model-verification", "AEGIS-authorization"),
        vertical_ip_refs=("aesirgrid:grid-models:v1",),
        customer_ip_refs=("customer:grid-operator:telemetry:v1",),
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


def _request(lease=None):
    return ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id="aesirgrid-predictive-maintenance",
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )


def test_staged_product_cannot_authorize_without_aegis_allow():
    product = _staged_product()
    admission = admit_controlled_action(_request())

    assert admission.decision is AegisDecision.ESCALATE
    with pytest.raises(ValueError, match="ALLOW admission"):
        authorize_product(product, admission)

    assert product.lifecycle_state is ProductLifecycle.STAGED


def test_valid_lease_permits_explicit_staged_to_authorized_transition():
    from hoare_engine.aesirgrid_authority import AuthorityLease, AuthorityStatus

    product = _staged_product()
    lease = AuthorityLease(
        lease_id="lease-aesirgrid-001",
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )
    admission = admit_controlled_action(_request(lease))

    assert admission.decision is AegisDecision.ALLOW
    authorized = authorize_product(product, admission)
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False


def test_authorization_does_not_grant_product_execution_authority():
    product = _staged_product()
    from hoare_engine.aesirgrid_authority import AuthorityLease, AuthorityStatus

    admission = admit_controlled_action(
        _request(
            AuthorityLease(
                lease_id="lease-aesirgrid-002",
                tenant_id="tenant-grid-001",
                product_id=product.product_id,
                mode=AesirGridMode.CONTROLLED,
                issued_at_s=100.0,
                expires_at_s=200.0,
                status=AuthorityStatus.VALID,
            )
        )
    )
    authorized = authorize_product(product, admission)

    assert authorized.authority == "product-definition-only"
    assert authorized.can_execute is False
