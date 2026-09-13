"""Governed proprietary-product factory contracts for HOARE.

Provenance: 2026-09-13

This module defines the platform-neutral control-plane representation of a
Tech Fusion product. It deliberately does not deploy or execute anything.
Generation, deployment, and consequential execution remain downstream
operations that require their own verification and AEGIS authorization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

SCHEMA_VERSION = "hoare.product-factory.v1"
FACTORY_VERSION = "1.0.0"


class ProductFactoryError(ValueError):
    """Raised when a product definition violates factory invariants."""


class ProductLifecycle(str, Enum):
    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    BUILDING = "BUILDING"
    TESTING = "TESTING"
    VERIFIED = "VERIFIED"
    STAGED = "STAGED"
    AUTHORIZED = "AUTHORIZED"
    DEPLOYED = "DEPLOYED"
    OPERATING = "OPERATING"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


_ALLOWED_TRANSITIONS: dict[ProductLifecycle, frozenset[ProductLifecycle]] = {
    ProductLifecycle.DRAFT: frozenset({ProductLifecycle.PLANNED}),
    ProductLifecycle.PLANNED: frozenset({ProductLifecycle.BUILDING}),
    ProductLifecycle.BUILDING: frozenset({ProductLifecycle.TESTING}),
    ProductLifecycle.TESTING: frozenset({ProductLifecycle.VERIFIED}),
    ProductLifecycle.VERIFIED: frozenset({ProductLifecycle.STAGED}),
    ProductLifecycle.STAGED: frozenset({ProductLifecycle.AUTHORIZED}),
    ProductLifecycle.AUTHORIZED: frozenset({ProductLifecycle.DEPLOYED}),
    ProductLifecycle.DEPLOYED: frozenset({ProductLifecycle.OPERATING}),
    ProductLifecycle.OPERATING: frozenset(
        {ProductLifecycle.SUSPENDED, ProductLifecycle.RETIRED}
    ),
    ProductLifecycle.SUSPENDED: frozenset(
        {ProductLifecycle.AUTHORIZED, ProductLifecycle.RETIRED}
    ),
    ProductLifecycle.RETIRED: frozenset(),
}


@dataclass(frozen=True)
class ProductDefinition:
    """A governed composition of reusable HOARE capabilities and vertical IP."""

    product_id: str
    product_version: str
    owner: str
    domain: str
    capabilities: tuple[str, ...] = ()
    domain_policies: tuple[str, ...] = ()
    workflows: tuple[str, ...] = ()
    integrations: tuple[str, ...] = ()
    deployment_profiles: tuple[str, ...] = ()
    compliance_profiles: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()
    lifecycle_state: ProductLifecycle = ProductLifecycle.DRAFT
    vertical_ip_refs: tuple[str, ...] = ()
    customer_ip_refs: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = {
            "product_id": self.product_id,
            "product_version": self.product_version,
            "owner": self.owner,
            "domain": self.domain,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise ProductFactoryError(
                "missing required product fields: " + ", ".join(missing)
            )
        if self.owner != "Tech Fusion AI ML LLC":
            raise ProductFactoryError("product owner must be Tech Fusion AI ML LLC")
        if any(not item.strip() for item in self.capabilities):
            raise ProductFactoryError("capability identifiers cannot be empty")

    @property
    def can_execute(self) -> bool:
        """Product definitions are never execution authority."""

        return False

    @property
    def authority(self) -> str:
        return "product-definition-only"

    def transition(self, target: ProductLifecycle) -> "ProductDefinition":
        """Return a new definition at a valid lifecycle state."""

        allowed = _ALLOWED_TRANSITIONS[self.lifecycle_state]
        if target not in allowed:
            raise ProductFactoryError(
                f"invalid lifecycle transition: "
                f"{self.lifecycle_state.value} -> {target.value}"
            )
        return ProductDefinition(
            **{
                **self.__dict__,
                "lifecycle_state": target,
            }
        )


def build_product_definition(
    *,
    product_id: str,
    product_version: str,
    domain: str,
    capabilities: Iterable[str] = (),
    domain_policies: Iterable[str] = (),
    workflows: Iterable[str] = (),
    integrations: Iterable[str] = (),
    deployment_profiles: Iterable[str] = (),
    compliance_profiles: Iterable[str] = (),
    evidence_requirements: Iterable[str] = (),
    vertical_ip_refs: Iterable[str] = (),
    customer_ip_refs: Iterable[str] = (),
    metadata: dict[str, str] | None = None,
) -> ProductDefinition:
    """Create a Tech Fusion product definition without authorizing execution."""

    return ProductDefinition(
        product_id=product_id,
        product_version=product_version,
        owner="Tech Fusion AI ML LLC",
        domain=domain,
        capabilities=tuple(dict.fromkeys(item.strip() for item in capabilities if item.strip())),
        domain_policies=tuple(dict.fromkeys(item.strip() for item in domain_policies if item.strip())),
        workflows=tuple(dict.fromkeys(item.strip() for item in workflows if item.strip())),
        integrations=tuple(dict.fromkeys(item.strip() for item in integrations if item.strip())),
        deployment_profiles=tuple(
            dict.fromkeys(item.strip() for item in deployment_profiles if item.strip())
        ),
        compliance_profiles=tuple(
            dict.fromkeys(item.strip() for item in compliance_profiles if item.strip())
        ),
        evidence_requirements=tuple(
            dict.fromkeys(item.strip() for item in evidence_requirements if item.strip())
        ),
        vertical_ip_refs=tuple(dict.fromkeys(item.strip() for item in vertical_ip_refs if item.strip())),
        customer_ip_refs=tuple(dict.fromkeys(item.strip() for item in customer_ip_refs if item.strip())),
        metadata=dict(metadata or {}),
    )


__all__ = [
    "FACTORY_VERSION",
    "ProductDefinition",
    "ProductFactoryError",
    "ProductLifecycle",
    "SCHEMA_VERSION",
    "build_product_definition",
]
