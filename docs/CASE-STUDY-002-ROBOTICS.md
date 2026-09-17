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
6. Action scope is explicit.
7. Expired authority is denied.
8. Authorization moves a staged product only after an `ALLOW` admission.

## IP boundary

Vertical and customer IP remain separate:

- Vertical IP: `robotics:inspection-models:v1`
- Customer IP: `customer:factory:robot-telemetry:v1`

## Why this matters

Case Study #1 used an energy-grid problem. Case Study #2 uses industrial robotics but reuses the same platform-level contracts.

That provides a direct architectural comparison:

| Concern | AesirGrid | Robotics |
|---|---|---|
| Product factory | Same | Same |
| Lifecycle | Same | Same |
| Authority model | Same | Same |
| Tenant boundary | Same | Same |
| Evidence boundary | Same pattern | Same pattern |
| AEGIS admission | Same | Same |
| Domain capabilities | Grid/energy | Robotics |
| Domain policy | Energy safety | Robotics safety |
| Vertical IP | Grid models | Inspection models |
| Customer IP | Grid telemetry | Factory telemetry |

The important result is not that the two products are identical. It is that **domain specialization occurs in capabilities, policies, workflows, integrations, and IP while the core governance contract remains reusable**.

## Test entry point

```text
backend/tests/test_case_study_robotics.py
```

Run the focused test locally:

```bash
cd backend
pytest tests/test_case_study_robotics.py -v
```

## Boundary

This case study does not authorize autonomous physical robot motion by itself. The injected/existing executor boundary remains downstream of admission. Any production robotics deployment requires its own safety validation, evidence, authority, and operational controls.
