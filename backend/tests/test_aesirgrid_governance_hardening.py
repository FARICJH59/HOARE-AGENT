"""Regression tests for AesirGrid governance hardening.

Provenance: 2026-09-16
"""

from hoare_engine.aesirgrid_case_study import AegisDecision, AesirGridMode, GridTelemetry, SyntheticGridTelemetryProvider, assess_asset, evaluate_aegis, run_aesirgrid_shadow
from hoare_engine.aesirgrid_authority import AuthorityLease, ControlledActionRequest, admit_controlled_action


def _nominal():
    return GridTelemetry("substation-001", 58.0, 2.0, 72.0, 60.01, 1000.0)


def _lease():
    return AuthorityLease(lease_id="lease-001", tenant_id="tenant-grid-001", product_id="aesirgrid-predictive-maintenance", action="apply_maintenance_setpoint", mode=AesirGridMode.CONTROLLED, issued_at_s=100.0, expires_at_s=200.0)


def test_empty_shadow_provider_is_denied():
    assessments, decision = run_aesirgrid_shadow(SyntheticGridTelemetryProvider([]))
    assert assessments == ()
    assert decision.decision is AegisDecision.DENY
    assert decision.reason == "no telemetry assessments available"


def test_empty_assessments_are_denied_in_simulation():
    decision = evaluate_aegis(mode=AesirGridMode.SIMULATION, assessments=(), telemetry_fresh=True, evidence_complete=True)
    assert decision.decision is AegisDecision.DENY
    assert decision.reason == "no telemetry assessments available"


def test_non_string_action_fails_closed_without_exception():
    request = ControlledActionRequest(tenant_id="tenant-grid-001", product_id="aesirgrid-predictive-maintenance", action=None, requested_mode=AesirGridMode.CONTROLLED, now_s=150.0, lease=_lease())
    result = admit_controlled_action(request)
    assert result.decision is AegisDecision.DENY
    assert result.reason == "controlled action is required"


def test_empty_string_action_is_denied_with_valid_lease():
    request = ControlledActionRequest(tenant_id="tenant-grid-001", product_id="aesirgrid-predictive-maintenance", action="", requested_mode=AesirGridMode.CONTROLLED, now_s=150.0, lease=_lease())
    result = admit_controlled_action(request)
    assert result.decision is AegisDecision.DENY
    assert result.reason == "controlled action is required"


def test_nominal_assessment_remains_unchanged():
    assessment = assess_asset(_nominal())
    assert assessment.asset_id == "substation-001"
    assert assessment.anomaly is False
    assert assessment.health_score == 1.0
