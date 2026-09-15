"""Tests for HOARE Case Study #1 synthetic simulation/shadow layer.

Provenance: 2026-09-12
"""

import pytest

from hoare_engine.aesirgrid_case_study import (
    AegisDecision,
    AesirGridMode,
    GridTelemetry,
    SyntheticGridTelemetryProvider,
    assess_asset,
    evaluate_aegis,
    run_aesirgrid_shadow,
)


def _nominal() -> GridTelemetry:
    return GridTelemetry(
        asset_id="substation-001",
        temperature_c=58.0,
        vibration_mm_s=2.0,
        load_pct=72.0,
        frequency_hz=60.01,
        timestamp_s=1000.0,
    )


def _anomalous() -> GridTelemetry:
    return GridTelemetry(
        asset_id="substation-002",
        temperature_c=104.0,
        vibration_mm_s=9.0,
        load_pct=94.0,
        frequency_hz=59.70,
        timestamp_s=1000.0,
    )


def test_simulation_detects_predictive_maintenance_signal():
    assessment = assess_asset(_anomalous())

    assert assessment.asset_id == "substation-002"
    assert assessment.anomaly is True
    assert assessment.health_score < 0.70
    assert assessment.confidence >= 0.90
    assert "high-temperature" in assessment.reason
    assert "high-vibration" in assessment.reason


def test_shadow_workflow_uses_provider_boundary_and_aegis_allows_analysis():
    provider = SyntheticGridTelemetryProvider([_nominal(), _anomalous()])

    assessments, decision = run_aesirgrid_shadow(provider)

    assert len(assessments) == 2
    assert {item.asset_id for item in assessments} == {
        "substation-001",
        "substation-002",
    }
    assert decision.decision is AegisDecision.ALLOW
    assert decision.mode is AesirGridMode.SHADOW
    assert "no physical control" in decision.reason
    assert "telemetry-integrity" in decision.evidence
    assert "model-verification" in decision.evidence
    assert "evidence-complete" in decision.evidence


def test_stale_telemetry_is_denied():
    decision = evaluate_aegis(
        mode=AesirGridMode.SHADOW,
        assessments=(assess_asset(_nominal()),),
        telemetry_fresh=False,
        evidence_complete=True,
    )

    assert decision.decision is AegisDecision.DENY
    assert decision.reason == "stale telemetry"


def test_incomplete_evidence_is_denied():
    decision = evaluate_aegis(
        mode=AesirGridMode.SHADOW,
        assessments=(assess_asset(_nominal()),),
        telemetry_fresh=True,
        evidence_complete=False,
    )

    assert decision.decision is AegisDecision.DENY
    assert "evidence" in decision.reason


def test_controlled_and_live_boundaries_escalate():
    assessment = assess_asset(_nominal())

    for mode in (AesirGridMode.CONTROLLED, AesirGridMode.LIVE):
        decision = evaluate_aegis(
            mode=mode,
            assessments=(assessment,),
            telemetry_fresh=True,
            evidence_complete=True,
        )
        assert decision.decision is AegisDecision.ESCALATE
        assert "explicit authority" in decision.reason


def test_invalid_telemetry_fails_closed():
    invalid = GridTelemetry(
        asset_id="substation-invalid",
        temperature_c=58.0,
        vibration_mm_s=-1.0,
        load_pct=72.0,
        frequency_hz=60.0,
        timestamp_s=1000.0,
    )

    with pytest.raises(ValueError, match="invalid telemetry range"):
        assess_asset(invalid)
