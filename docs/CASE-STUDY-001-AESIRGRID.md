# HOARE Case Study #1 — AesirGrid Predictive Maintenance

**Provenance:** 2026-09-12  
**Case study ID:** `HOARE-CS-001`  
**Platform owner:** Tech Fusion AI ML LLC  
**Vertical:** AesirGrid / energy

## Purpose

This is the first formal case study for validating **HOARE itself**, rather than validating only an individual vertical application.

The question is:

> Can one real enterprise intent move through HOARE's governed product-factory boundary into a verified, staged proprietary product definition without creating a separate platform or granting the generated product execution authority?

## Business intent

> Build an energy-grid predictive-maintenance system for AesirGrid using telemetry from grid assets.

## Governed flow

```text
INTENT
  ↓
UNDERSTAND
  ↓
ARCHITECT
  ↓
CAPABILITY DISCOVERY
  ↓
REUSE / COMPOSE / EXTEND / CREATE
  ↓
BUILD
  ↓
TEST
  ↓
VERIFY
  ↓
AEGIS REVIEW
  ↓
STAGED
  ↓
[explicit AUTHORIZED boundary]
  ↓
DEPLOYED
  ↓
OPERATING
```

The implemented case study currently proves the control-plane portion through `STAGED`. It deliberately does **not** pretend that a product definition is deployment authority.

## Product composition

The case study composes these capabilities:

- Telemetry
- PredictiveMaintenance
- AssetHealthScoring
- AnomalyDetection

It binds the product to:

- energy policy: `energy.grid.safety.v1`
- telemetry ingestion and asset-health workflows
- grid telemetry integration
- simulation, shadow, controlled, and live deployment profiles
- NIST-AI-RMF compliance profile
- telemetry-integrity, model-verification, and AEGIS-authorization evidence requirements

## IP boundary

The case study explicitly keeps vertical IP and customer IP separate:

- Vertical IP: `aesirgrid:grid-models:v1`
- Customer IP: `customer:grid-operator:telemetry:v1`

This is a required property of the Tech Fusion product factory. Customer data and customer-specific artifacts must not become Tech Fusion vertical IP merely because HOARE used them to build or operate a solution.

## Governance proof

The case study verifies that:

1. The product is owned by Tech Fusion AI ML LLC.
2. The lifecycle advances sequentially through `PLANNED → BUILDING → TESTING → VERIFIED → STAGED`.
3. The product definition has `product-definition-only` authority.
4. `can_execute` remains false.
5. `STAGED` cannot jump directly to `DEPLOYED`.
6. Vertical IP and customer IP remain distinct.
7. Evidence requirements are part of the product definition.

## What this proves

This case study is stronger than a collection of unrelated unit tests because it binds one enterprise intent to one concrete vertical product definition and carries that definition through a governed lifecycle.

It is **not yet a live AesirGrid deployment test**. Live telemetry, model execution, infrastructure provisioning, and production control remain separate governed operations that require their own adapters, verification, evidence, and AEGIS authorization.

## Test entry point

```text
backend/tests/test_case_study_aesirgrid.py
```

Run the case study from the repository's backend environment with:

```bash
cd backend
pytest tests/test_case_study_aesirgrid.py -v
```

## Enterprise validation criterion

HOARE Case Study #1 is considered complete at the control-plane level when the case-study test passes and demonstrates the complete governed path from business intent to `STAGED` without bypassing authorization boundaries.

The next validation layer is a provider-backed AesirGrid simulation/shadow workflow. That layer should be added without changing the core product-factory contract or replacing the existing executor.
