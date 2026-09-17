"""HOARE Case Study #1 controlled authorization proof.

Provenance: 2026-09-16

This test joins the existing product-factory and authority contracts. It does
not execute a physical command; it proves that the authorization boundary is
reached only by an exactly scoped, valid, evidence-carrying lease.
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
ACTION = "apply_maintenance_setpoint"


def _staged_product():
    product = build_product_definition(
        product_id=PRODUCT_ID,
        product_version="1.0.0",
        domain="energy",
        capabilities=(
            "Telemetry",
            "PredictiveMaintenance",
            "AssetHealthScoring",
            "AnomalyDetection",
        ),
        evidence_requirements=(
            "telemetry-integrity",
            "model-verification",
            "AEGIS-authorization",
        ),
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


def _valid_lease(**overrides):
    values = dict(
        lease_id="lease-aesirgrid-controlled-001",
        tenant_id=TENANT_ID,
        product_id=PRODUCT_ID,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
        action=ACTION,
        authority_source="human-operator-approval",
        evidence_refs=("telemetry-integrity", "model-verification"),
        scope=(ACTION,),
        audit_correlation_id="audit-aesirgrid-001",
    )
    values.update(overrides)
    return AuthorityLease(**values)


def _request(**overrides):
    values = dict(
        tenant_id=TENANT_ID,
        product_id=PRODUCT_ID,
        action=ACTION,
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=_valid_lease(),
    )
    values.update(overrides)
    return ControlledActionRequest(**values)


def test_aesirgrid_controlled_case_study_reaches_authorized_boundary():
    product = _staged_product()
    admission = admit_controlled_action(_request())

    assert admission.decision is AegisDecision.ALLOW
    assert admission.evidence_refs == ("telemetry-integrity", "model-verification")
    assert admission.audit_correlation_id == "audit-aesirgrid-001"

    authorized = authorize_product(product, admission)
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.authority == "product-definition-only"
    assert authorized.can_execute is False


def test_aesirgrid_lease_is_exactly_bound_to_action():
    result = admit_controlled_action(
        _request(lease=_valid_lease(action="different_action"))
    )

    assert result.decision is AegisDecision.DENY
    assert result.reason == "authority lease action mismatch"


def test_aesirgrid_action_outside_scope_is_denied():
    result = admit_controlled_action(
        _request(lease=_valid_lease(scope=("other_action",)))
    )

    assert result.decision is AegisDecision.DENY
    assert result.reason == "authority action outside lease scope"


def test_aesirgrid_live_request_requires_live_scoped_lease():
    result = admit_controlled_action(
        _request(
            requested_mode=AesirGridMode.LIVE,
            lease=_valid_lease(mode=AesirGridMode.CONTROLLED),
        )
    )

    assert result.decision is AegisDecision.DENY
    assert result.reason == "authority lease mode mismatch"


def test_aesirgrid_no_lease_escalates_before_authorization():
    admission = admit_controlled_action(_request(lease=None))

    assert admission.decision is AegisDecision.ESCALATE
    with pytest.raises(ValueError, match="ALLOW admission"):
        authorize_product(_staged_product(), admission)


def test_aesirgrid_wrong_tenant_cannot_use_valid_lease():
    admission = admit_controlled_action(_request(tenant_id="other-tenant"))

    assert admission.decision is AegisDecision.DENY
    assert admission.reason == "authority lease tenant mismatch"


def test_aesirgrid_expired_lease_cannot_authorize_product():
    admission = admit_controlled_action(_request(now_s=200.0))

    assert admission.decision is AegisDecision.DENY
    assert admission.reason == "authority lease is expired or revoked"
    with pytest.raises(ValueError, match="ALLOW admission"):
        authorize_product(_staged_product(), admission)


def test_aesirgrid_missing_evidence_cannot_authorize_product():
    admission = admit_controlled_action(_request(lease=_valid_lease(evidence_refs=())))

    assert admission.decision is AegisDecision.DENY
    assert admission.reason == "authority evidence is required"
