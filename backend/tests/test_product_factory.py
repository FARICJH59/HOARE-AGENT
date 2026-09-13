"""Tests for the governed proprietary-product factory contract.

Provenance: 2026-09-13
"""

import pytest

from hoare_engine.product_factory import (
    ProductFactoryError,
    ProductLifecycle,
    build_product_definition,
)


def test_product_definition_composes_reusable_capabilities() -> None:
    product = build_product_definition(
        product_id="aesirgrid",
        product_version="1.0.0",
        domain="energy",
        capabilities=["Telemetry", "PredictiveMaintenance", "Telemetry"],
        domain_policies=["energy.grid.safety.v1"],
        compliance_profiles=["NIST-AI-RMF"],
        vertical_ip_refs=["aesirgrid:grid-models:v1"],
    )

    assert product.owner == "Tech Fusion AI ML LLC"
    assert product.capabilities == ("Telemetry", "PredictiveMaintenance")
    assert product.lifecycle_state is ProductLifecycle.DRAFT
    assert product.authority == "product-definition-only"
    assert product.can_execute is False


def test_product_lifecycle_is_explicit_and_sequential() -> None:
    product = build_product_definition(
        product_id="shelf-scouter",
        product_version="1.0.0",
        domain="retail",
    )

    product = product.transition(ProductLifecycle.PLANNED)
    product = product.transition(ProductLifecycle.BUILDING)
    product = product.transition(ProductLifecycle.TESTING)
    product = product.transition(ProductLifecycle.VERIFIED)
    product = product.transition(ProductLifecycle.STAGED)

    assert product.lifecycle_state is ProductLifecycle.STAGED


def test_invalid_lifecycle_transition_is_rejected() -> None:
    product = build_product_definition(
        product_id="industrial-ai",
        product_version="1.0.0",
        domain="manufacturing",
    )

    with pytest.raises(ProductFactoryError, match="invalid lifecycle transition"):
        product.transition(ProductLifecycle.DEPLOYED)


def test_product_cannot_be_owned_by_customer_or_self_authorize() -> None:
    with pytest.raises(ProductFactoryError, match="product owner"):
        from hoare_engine.product_factory import ProductDefinition

        ProductDefinition(
            product_id="customer-product",
            product_version="1.0.0",
            owner="Customer A",
            domain="healthcare",
        )

    product = build_product_definition(
        product_id="healthfusion",
        product_version="1.0.0",
        domain="healthcare",
    )
    assert product.can_execute is False


def test_customer_ip_is_separate_from_vertical_ip() -> None:
    product = build_product_definition(
        product_id="manufacturing-ai",
        product_version="1.0.0",
        domain="manufacturing",
        vertical_ip_refs=["vertical:maintenance-model:v1"],
        customer_ip_refs=["customer:factory-a:private-model:v7"],
    )

    assert product.vertical_ip_refs == ("vertical:maintenance-model:v1",)
    assert product.customer_ip_refs == ("customer:factory-a:private-model:v7",)
