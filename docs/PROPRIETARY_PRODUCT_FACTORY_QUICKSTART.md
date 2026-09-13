# HOARE Product Factory Quickstart

**Provenance:** 2026-09-13

The product-factory contract makes the business architecture executable as a platform concern:

- **Tech Fusion AI ML LLC** owns the product portfolio.
- **HOARE.AI** supplies the reusable control plane and agentic engineering factory.
- **Vertical products** compose reusable capabilities plus domain-specific IP.
- **Customer IP** remains isolated from both core and vertical IP.
- A product definition is **never execution authority**.

## Example

```python
from hoare_engine.product_factory import build_product_definition, ProductLifecycle

product = build_product_definition(
    product_id="aesirgrid",
    product_version="1.0.0",
    domain="energy",
    capabilities=(
        "telemetry",
        "digital_twin",
        "predictive_maintenance",
        "vpp_orchestration",
    ),
    compliance_profiles=("energy.grid.safety.v1",),
    vertical_ip_refs=("aesirgrid:grid-models:v1",),
)

product = product.transition(ProductLifecycle.PLANNED)
```

This only creates a governed product definition. It does **not** authorize deployment or physical execution.

## Factory rule

A new vertical should first ask the capability registry whether an existing capability can be:

1. reused;
2. composed;
3. extended; or
4. created as a genuinely missing capability.

Only after verification and governance should the resulting product move through staging and authorization.

## Long-term composition

```text
                 HOARE.AI
                    │
          Capability Registry
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
   AesirGrid   Shelf-Scouter  Industrial AI
       │            │            │
       └────────────┼────────────┘
                    ▼
             Reusable Assets
                    │
                    ▼
             Next Product
```

The objective is a compounding factory, not a collection of duplicated vertical platforms.
