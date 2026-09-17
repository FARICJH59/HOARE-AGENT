# HOARE Case Study #2 — Industrial Robotics

**Provenance:** 2026-09-16  
**Case study ID:** `HOARE-CS-002`  
**Vertical:** industrial robotics

## Purpose

Case Study #2 tests the central architectural claim that HOARE is vertical-neutral. It uses the same product-factory contract and governance principles as Case Study #1, but changes the domain from energy to industrial robotics.

## Business intent

> Build a predictive-maintenance and safety-monitoring system for industrial robots using robot telemetry.

## Flow

```text
INTENT
  ↓
HOARE PRODUCT FACTORY
  ↓
ROBOTICS PRODUCT DEFINITION
  ↓
PLANNED → BUILDING → TESTING → VERIFIED → STAGED
  ↓
ROBOT TELEMETRY
  ↓
HEALTH / MAINTENANCE ASSESSMENT
  ↓
SAFETY CHECK
  ↓
EVIDENCE CHECK
  ↓
AEGIS GOVERNANCE
  ├── DENY
  ├── ESCALATE → explicit authority
  └── ALLOW
       ↓
SIMULATION / SHADOW ANALYSIS
```

## Capabilities

The product composes:

- Telemetry
- PredictiveMaintenance
- SafetyMonitoring

The product binds to robotics-specific policy, workflows, controller integration, industrial-safety evidence, and separate vertical/customer IP references.

## Governance cases

The test suite deliberately exercises:

- normal telemetry
- maintenance-signaling telemetry
- incomplete evidence
- unsafe robot zone
- controlled mode without authority
- live mode with explicit authority
- invalid telemetry

The key invariant is that an AI recommendation does not itself constitute physical authority.

## Vertical-neutrality evidence

The implementation uses the same `build_product_definition()` and `ProductLifecycle` contract used by AesirGrid while changing the domain, capabilities, policies, workflows, integration, compliance profile, and IP references.

That is the architectural experiment:

```text
AesirGrid                    Robotics
    │                            │
    └────────── HOARE ───────────┘
                 │
        same factory contract
        same lifecycle boundary
        same authority principle
```

## Safety boundary

Simulation and shadow analysis are explicitly non-actuating. Controlled/live operation requires an explicit authority decision. An unsafe physical condition is denied even when authority is present.

This case study does not connect to a physical robot, issue motion commands, or replace the existing executor.

## Test entry point

```text
backend/tests/test_case_study_robotics.py
```

Run locally:

```bash
cd backend
pytest tests/test_case_study_robotics.py -v
```

## Validation criterion

Case Study #2 validates vertical neutrality at the product-factory/governance layer when the robotics test suite passes without adding an AesirGrid-specific dependency to the factory contract.
