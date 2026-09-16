"""Tests for evidence-bound governed execution.

Provenance: 2026-09-16
"""

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    AuthorityStatus,
    ControlledActionRequest,
    admit_controlled_action,
    authorize_product,
)
from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode
from hoare_engine.governed_evidence_execution import execute_governed_with_evidence
from hoare_engine.product_factory import ProductLifecycle, build_product_definition


def _staged_product():
    product = build_product_definition(
        product_id="aesirgrid-predictive-maintenance",
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


def _lease(product):
    return AuthorityLease(
        lease_id="lease-evidence-001",
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
    )


def _request(product, lease=None):
    return ControlledActionRequest(
        tenant_id="tenant-grid-001",
        product_id=product.product_id,
        action="apply_maintenance_setpoint",
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )


def test_denied_execution_still_produces_nonsecret_evidence():
    product = _staged_product()
    calls = []

    result = execute_governed_with_evidence(
        _request(product),
        lambda: calls.append("executed"),
        product=product,
        case_study_id="HOARE-CS-001",
        telemetry_payload={"asset_id": "substation-001", "frequency_hz": 60.01},
        evidence=("telemetry-integrity", "model-verification"),
    )

    assert result.execution.admission.decision is AegisDecision.ESCALATE
    assert result.execution.executed is False
    assert calls == []
    assert result.evidence.decision is AegisDecision.ESCALATE
    assert result.evidence.authority_lease_id is None
    assert len(result.evidence.telemetry_digest) == 64
    assert len(result.evidence.event_digest) == 64


def test_authorized_execution_binds_lease_and_execution_facts_into_evidence():
    staged = _staged_product()
    lease = _lease(staged)
    admission = admit_controlled_action(_request(staged, lease))
    authorized = authorize_product(staged, admission)
    calls = []

    result = execute_governed_with_evidence(
        _request(authorized, lease),
        lambda: calls.append("executed") or "executor-result",
        product=authorized,
        case_study_id="HOARE-CS-001",
        telemetry_payload={"asset_id": "substation-002", "frequency_hz": 59.70},
        evidence=("telemetry-integrity", "model-verification", "AEGIS-authorization"),
        event_fields={"stage": "controlled-admission"},
    )

    assert result.execution.admission.decision is AegisDecision.ALLOW
    assert result.execution.executed is True
    assert result.execution.result == "executor-result"
    assert calls == ["executed"]
    assert result.evidence.decision is AegisDecision.ALLOW
    assert result.evidence.authority_lease_id == "lease-evidence-001"
    assert result.evidence.to_dict()["decision"] == "ALLOW"
    assert result.evidence.to_dict()["authority_lease_id"] == "lease-evidence-001"


def test_evidence_changes_when_execution_result_changes():
    product = _staged_product()
    lease = _lease(product)
    admission = admit_controlled_action(_request(product, lease))
    authorized = authorize_product(product, admission)

    first = execute_governed_with_evidence(
        _request(authorized, lease),
        lambda: "first",
        product=authorized,
        case_study_id="HOARE-CS-001",
        telemetry_payload={"asset": "same"},
        evidence=("model-verification",),
        event_fields={"attempt": 1},
    )
    second = execute_governed_with_evidence(
        _request(authorized, lease),
        lambda: "second",
        product=authorized,
        case_study_id="HOARE-CS-001",
        telemetry_payload={"asset": "same"},
        evidence=("model-verification",),
        event_fields={"attempt": 2},
    )

    assert first.evidence.event_digest != second.evidence.event_digest
