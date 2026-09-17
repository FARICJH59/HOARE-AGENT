# HOARE Case Study #2 — Industrial Robotics

**Provenance:** 2026-09-16  
**Case study ID:** `HOARE-CS-002`  
**Platform owner:** Tech Fusion AI ML LLC  
**Vertical:** industrial robotics

## Purpose

Case Study #2 changes the industry while deliberately reusing the same HOARE control-plane contracts validated by Case Study #1.

The purpose is to test the architectural claim that HOARE is **vertical-neutral**: the domain changes, while the governed product lifecycle and authorization model remain reusable.

## Business intent

> Build a governed robotic inspection and predictive-maintenance system.

## Reused HOARE contract

```text
INTENT
  ↓
PRODUCT DEFINITION
  ↓
PLANNED → BUILDING → TESTING → VERIFIED → STAGED
  ↓
AUTHORITY LEASE
  ↓
AEGIS ADMISSION
  ├── DENY
  ├── ESCALATE
  └── ALLOW
  ↓
AUTHORIZED
  ↓
existing executor boundary
```

No robotics-specific replacement for the HOARE product factory is introduced.

## Robotics composition

The product composes:

- MachineVision
- RobotStateMonitoring
- AnomalyDetection
- PredictiveMaintenance

It binds:

- `robotics.safety.v1`
- robot telemetry and inspection workflows
- a robot-controller adapter boundary
- simulation, shadow, controlled, and live deployment profiles
- an industrial-safety compliance profile
- sensor-integrity, model-verification, and safety-authorization evidence

## Governance tests

The case study verifies that:

1. A robotics product can use the same product-factory lifecycle.
2. Product definitions remain non-execution authority.
3. Controlled action requires an explicit authority lease.
4. Tenant identity remains bound to the lease.
5. Product identity remains bound to the lease.
6. Action identity and scope remain explicit.
7. Expired authority is denied.
8. Authorization moves a staged product only after an `ALLOW` admission.
9. Unsafe physical conditions are denied before actuation.
10. Simulation and shadow remain non-actuating.

## IP boundary

Vertical and customer IP remain separate:

- Vertical IP: `robotics:inspection-models:v1`
- Customer IP: `customer:factory:robot-telemetry:v1`

## Why this matters

Case Study #1 used an energy-grid problem. Case Study #2 uses industrial robotics but reuses the same platform-level contracts.

```text
AesirGrid                    Robotics
    │                            │
    └────────── HOARE ───────────┘
                 │
        same factory contract
        same lifecycle boundary
        same authority principle
```

Domain specialization occurs in capabilities, policies, workflows, integrations, compliance evidence, and IP while the core governance contract remains reusable.

## Boundary

This case study does not authorize autonomous physical robot motion by itself. Any production robotics deployment requires its own safety validation, evidence, authority, and operational controls.

## Test entry point

```text
backend/tests/test_case_study_robotics.py
```

Run locally:

```bash
cd backend
pytest tests/test_case_study_robotics.py -v
```
