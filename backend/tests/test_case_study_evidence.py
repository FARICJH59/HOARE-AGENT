"""Tests for the auditable HOARE case-study evidence bundle.

Provenance: 2026-09-16
"""

from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode
from hoare_engine.case_study_evidence import build_evidence_bundle, digest_payload


def test_evidence_bundle_is_deterministic_and_hash_bound():
    kwargs = dict(
        case_study_id="HOARE-CS-001",
        product_id="aesirgrid-predictive-maintenance",
        tenant_id="tenant-grid-001",
        mode=AesirGridMode.SHADOW,
        decision=AegisDecision.ALLOW,
        evidence=("telemetry-integrity", "model-verification", "evidence-complete"),
        telemetry_digest=digest_payload({"asset": "substation-001", "frequency": 60.01}),
        authority_lease_id=None,
        event_fields={"stage": "shadow-analysis"},
    )

    first = build_evidence_bundle(**kwargs)
    second = build_evidence_bundle(**kwargs)

    assert first.event_digest == second.event_digest
    assert len(first.event_digest) == 64
    assert first.telemetry_digest != ""
    assert first.authority_lease_id is None


def test_evidence_bundle_changes_when_governance_decision_changes():
    common = dict(
        case_study_id="HOARE-CS-001",
        product_id="aesirgrid-predictive-maintenance",
        tenant_id="tenant-grid-001",
        mode=AesirGridMode.SHADOW,
        evidence=("telemetry-integrity",),
        telemetry_digest=digest_payload({"asset": "substation-001"}),
        authority_lease_id=None,
        event_fields={"stage": "shadow-analysis"},
    )

    allowed = build_evidence_bundle(decision=AegisDecision.ALLOW, **common)
    denied = build_evidence_bundle(decision=AegisDecision.DENY, **common)

    assert allowed.event_digest != denied.event_digest


def test_evidence_bundle_contains_no_raw_credential_field():
    bundle = build_evidence_bundle(
        case_study_id="HOARE-CS-001",
        product_id="aesirgrid-predictive-maintenance",
        tenant_id="tenant-grid-001",
        mode=AesirGridMode.CONTROLLED,
        decision=AegisDecision.ALLOW,
        evidence=("model-verification", "AEGIS-authorization"),
        telemetry_digest="a" * 64,
        authority_lease_id="lease-aesirgrid-001",
        event_fields={"action": "apply_maintenance_setpoint"},
    )

    rendered = bundle.to_dict()
    assert "token" not in rendered
    assert "secret" not in rendered
    assert "credential" not in rendered
    assert rendered["authority_lease_id"] == "lease-aesirgrid-001"
