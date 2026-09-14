# HOARE Case Study #1 — AesirGrid Predictive Maintenance

**Provenance:** 2026-09-12  
**Case study ID:** `HOARE-CS-001`  
**Platform owner:** Tech Fusion AI ML LLC  
**Vertical:** AesirGrid / energy

## Purpose

This is the first formal case study for validating **HOARE itself**, rather than validating only an individual vertical application.

The question is:

> Can one real enterprise intent move through HOARE's governed product factory, process synthetic grid telemetry, identify a maintenance signal, and reach a governed shadow decision without creating a separate platform or granting the generated product execution authority?

## Current proven flow

```text
INTENT
  ↓
PRODUCT DEFINITION
  ↓
CAPABILITY COMPOSITION
  ↓
PLANNED → BUILDING → TESTING → VERIFIED → STAGED
  ↓
SYNTHETIC GRID TELEMETRY
  ↓
PREDICTIVE-MAINTENANCE ASSESSMENT
  ↓
TELEMETRY / EVIDENCE CHECKS
  ↓
AEGIS SHADOW DECISION
  ↓
SHADOW ANALYSIS ALLOWED
  ↓
NO PHYSICAL CONTROL
```

The implemented case study now reaches the **provider-backed synthetic shadow boundary**. The provider is an explicit abstraction (`TelemetryProvider`) with a deterministic `SyntheticGridTelemetryProvider` implementation. No real grid or cloud provider is contacted.

## Product composition

The product definition composes:

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

## Synthetic telemetry

The case study uses deterministic synthetic assets with:

- temperature
- vibration
- load percentage
- grid frequency
- timestamp

A deliberately anomalous sample raises temperature, vibration, load, and frequency-deviation penalties. The resulting health score becomes an explicit predictive-maintenance signal.

## Governance proof

The shadow workflow verifies:

1. Telemetry is supplied through a provider boundary.
2. Invalid telemetry fails closed.
3. Predictive-maintenance assessment is deterministic and testable.
4. Fresh telemetry is required.
5. Required evidence is required.
6. Shadow analysis may be ALLOWED.
7. Shadow ALLOW explicitly means **analysis only; no physical control**.
8. `CONTROLLED` and `LIVE` modes require ESCALATE / explicit authority.
9. Stale telemetry is DENIED.
10. Incomplete evidence is DENIED.

## IP boundary

The case study keeps vertical IP and customer IP separate:

- Vertical IP: `aesirgrid:grid-models:v1`
- Customer IP: `customer:grid-operator:telemetry:v1`

## What this proves

This is now a stronger end-to-end HOARE case study:

```text
enterprise intent
      ↓
proprietary product definition
      ↓
verified/staged lifecycle
      ↓
synthetic telemetry provider
      ↓
predictive-maintenance analysis
      ↓
evidence + freshness gates
      ↓
AEGIS governance
      ↓
shadow analysis
```

It still does **not** claim live AesirGrid operation. No physical grid command, production deployment, or live control authority is implemented by this case study.

## Next validation boundary

The next step is a controlled-mode authorization test that demonstrates an explicit authority artifact/lease before any controlled action can be admitted. That should remain separate from the local high-frequency controller and should not replace the existing executor.

## Test entry points

```text
backend/tests/test_case_study_aesirgrid.py
backend/tests/test_aesirgrid_simulation.py
```

Run the focused suite locally:

```bash
cd backend
pytest tests/test_case_study_aesirgrid.py tests/test_aesirgrid_simulation.py -v
```
