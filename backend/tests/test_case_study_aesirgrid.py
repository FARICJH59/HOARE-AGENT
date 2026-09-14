"""Formal HOARE Case Study #1: AesirGrid predictive maintenance.

Provenance: 2026-09-12

This is intentionally a control-plane case study. It proves that one
enterprise intent can be represented, governed, verified, and staged without
creating a second platform or granting the product definition execution
authority.
"""

from hoare_engine.product_factory import ProductLifecycle, build_product_definition


def _aesirgrid_case_study():
    """Build the complete governed product lifecycle used by the case study."""
    intent = (
        "Build an energy-grid predictive-maintenance system for AesirGrid "
        "using telemetry from grid assets."
    )

    product = build_product_definition(
        product_id="aesirgrid-predictive-maintenance",
        product_version="1.0.0",
        domain="energy",
        capabilities=(
            "Telemetry",
            "PredictiveMaintenance",
            "AssetHealthScoring",
            "AnomalyDetection",
        ),
        domain_policies=("energy.grid.safety.v1",),
        workflows=("telemetry-ingestion", "asset-health-assessment"),
        integrations=("grid-telemetry",),
        deployment_profiles=("simulation", "shadow", "controlled", "live"),
        compliance_profiles=("NIST-AI-RMF",),
        evidence_requirements=(
            "telemetry-integrity",
            "model-verification",
            "AEGIS-authorization",
        ),
        vertical_ip_refs=("aesirgrid:grid-models:v1",),
        customer_ip_refs=("customer:grid-operator:telemetry:v1",),
        metadata={"intent": intent, "case_study": "HOARE-CS-001"},
    )

    lifecycle = (
        ProductLifecycle.PLANNED,
        ProductLifecycle.BUILDING,
        ProductLifecycle.TESTING,
        ProductLifecycle.VERIFIED,
        ProductLifecycle.STAGED,
    )
    for target in lifecycle:
        product = product.transition(target)

    return intent, product


def test_aesirgrid_case_study_completes_governed_build_to_staged():
    intent, product = _aesirgrid_case_study()

    assert intent.startswith("Build an energy-grid predictive-maintenance system")
    assert product.product_id == "aesirgrid-predictive-maintenance"
    assert product.domain == "energy"
    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.authority == "product-definition-only"
    assert product.can_execute is False
    assert product.capabilities == (
        "Telemetry",
        "PredictiveMaintenance",
        "AssetHealthScoring",
        "AnomalyDetection",
    )
    assert product.domain_policies == ("energy.grid.safety.v1",)
    assert product.evidence_requirements == (
        "telemetry-integrity",
        "model-verification",
        "AEGIS-authorization",
    )
    assert product.vertical_ip_refs == ("aesirgrid:grid-models:v1",)
    assert product.customer_ip_refs == ("customer:grid-operator:telemetry:v1",)
    assert product.metadata["case_study"] == "HOARE-CS-001"


def test_aesirgrid_case_study_requires_explicit_authorization_before_deploy():
    _, product = _aesirgrid_case_study()

    # STAGED cannot skip the explicit authorization boundary.
    assert product.lifecycle_state is ProductLifecycle.STAGED
    assert product.can_execute is False

    try:
        product.transition(ProductLifecycle.DEPLOYED)
    except ValueError as exc:
        assert "invalid lifecycle transition" in str(exc)
    else:
        raise AssertionError("STAGED must not transition directly to DEPLOYED")


def test_aesirgrid_case_study_preserves_vertical_and_customer_ip_boundaries():
    _, product = _aesirgrid_case_study()

    assert "aesirgrid:grid-models:v1" in product.vertical_ip_refs
    assert "customer:grid-operator:telemetry:v1" in product.customer_ip_refs
    assert set(product.vertical_ip_refs).isdisjoint(product.customer_ip_refs)
