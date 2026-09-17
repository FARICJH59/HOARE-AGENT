"""Integrated HOARE Case Study #1 controlled-boundary harness.

Provenance: 2026-09-17

This test composes the existing product-factory, telemetry/shadow, authority,
and injected-executor boundaries. It does not replace or directly implement
the production executor.
"""

from hoare_engine.aesirgrid_authority import (
    AuthorityLease,
    AuthorityStatus,
    ControlledActionRequest,
    admit_controlled_action,
    authorize_product,
    execute_authorized_action,
)
from hoare_engine.aesirgrid_case_study import (
    AegisDecision,
    AesirGridMode,
    GridTelemetry,
    SyntheticGridTelemetryProvider,
    run_aesirgrid_shadow,
)
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
        domain_policies=("energy.grid.safety.v1",),
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


def _valid_lease():
    return AuthorityLease(
        lease_id="lease-aesirgrid-controlled-001",
        tenant_id=TENANT_ID,
        product_id=PRODUCT_ID,
        action=ACTION,
        mode=AesirGridMode.CONTROLLED,
        issued_at_s=100.0,
        expires_at_s=200.0,
        status=AuthorityStatus.VALID,
        authority_source="human-operator-approval",
        evidence_refs=("telemetry-integrity", "model-verification"),
        scope=(ACTION,),
        audit_correlation_id="audit-aesirgrid-controlled-001",
    )


def _request(lease):
    return ControlledActionRequest(
        tenant_id=TENANT_ID,
        product_id=PRODUCT_ID,
        action=ACTION,
        requested_mode=AesirGridMode.CONTROLLED,
        now_s=150.0,
        lease=lease,
    )


def test_case_study_composes_intent_product_shadow_and_controlled_boundary():
    product = _staged_product()
    provider = SyntheticGridTelemetryProvider(
        [
            GridTelemetry(
                asset_id="substation-001",
                temperature_c=58.0,
                vibration_mm_s=2.0,
                load_pct=72.0,
                frequency_hz=60.01,
                timestamp_s=1000.0,
            ),
            GridTelemetry(
                asset_id="substation-002",
                temperature_c=104.0,
                vibration_mm_s=9.0,
                load_pct=94.0,
                frequency_hz=59.70,
                timestamp_s=1000.0,
            ),
        ]
    )

    assessments, shadow = run_aesirgrid_shadow(provider)
    admission = admit_controlled_action(_request(_valid_lease()))
    authorized = authorize_product(product, admission)

    executed = []

    def existing_executor(request):
        executed.append(request.action)
        return "controlled-operation-substrate"

    result = execute_authorized_action(_request(_valid_lease()), existing_executor)

    assert len(assessments) == 2
    assert any(item.anomaly for item in assessments)
    assert shadow.decision is AegisDecision.ALLOW
    assert shadow.mode is AesirGridMode.SHADOW
    assert admission.decision is AegisDecision.ALLOW
    assert authorized.lifecycle_state is ProductLifecycle.AUTHORIZED
    assert authorized.can_execute is False
    assert result == "controlled-operation-substrate"
    assert executed == [ACTION]


def test_case_study_stops_before_executor_when_authority_is_missing():
    calls = []

    def existing_executor(request):
        calls.append(request.action)
        return "must-not-run"

    request = _request(None)
    admission = admit_controlled_action(request)

    assert admission.decision is AegisDecision.ESCALATE

    try:
        execute_authorized_action(request, existing_executor)
    except PermissionError as exc:
        assert "ESCALATE" in str(exc)
    else:
        raise AssertionError("missing authority must not reach executor")

    assert calls == []
