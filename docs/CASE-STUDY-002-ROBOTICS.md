# HOARE Case Study #2 — Industrial Robotics Inspection

**Provenance:** 2026-09-16  
**Case study ID:** `HOARE-CS-002`  
**Platform owner:** Tech Fusion AI ML LLC  
**Vertical:** Industrial robotics

## Purpose

Case Study #2 tests the central architectural claim from a different domain: HOARE's control-plane and governance primitives can be reused for an industrial robotics product without creating a second platform.

## Business intent

> Build an industrial robot inspection and predictive-maintenance system using telemetry from factory robots.

## Governed flow

```text
INTENT
  ↓
HOARE PRODUCT FACTORY
  ↓
ROBOTICS PRODUCT DEFINITION
  ↓
PLANNED → BUILDING → TESTING → VERIFIED → STAGED
  ↓
SYNTHETIC ROBOT TELEMETRY
  ↓
INSPECTION / HEALTH ASSESSMENT
  ↓
EVIDENCE VALIDATION
  ↓
SHADOW ANALYSIS
  ↓
CONTROLLED REQUEST
  ↓
EXPLICIT AUTHORITY
```

## Product composition

The robotics product uses the same generic product-factory contract used by the AesirGrid case study, with a different domain and different capabilities:

- RobotTelemetry
- PredictiveMaintenance
- AnomalyDetection
- robot telemetry and controller integration boundaries
- robotics machine-safety policy
- inspection verification evidence

The product is intentionally `product-definition-only` and has no execution authority.

## Synthetic inspection

The deterministic test provider supplies:

- joint temperature
- vibration
- cycle time
- payload percentage
- timestamp

A degraded robot produces multiple independent maintenance signals. The inspection layer converts those signals into a health score and maintenance indicator.

## Governance

The case study validates:

1. A robotics product can use the existing universal product factory.
2. The lifecycle reaches `STAGED` through the same ordered states.
3. Shadow inspection can be allowed without physical robot control.
4. Stale telemetry is denied.
5. Invalid telemetry fails closed.
6. Controlled operation escalates for explicit authority.
7. The robotics domain does not require a new HOARE core.

## IP boundary

- Vertical IP: `robotics:inspection-models:v1`
- Customer IP: `customer:factory:robot-telemetry:v1`

These remain distinct, preserving the Tech Fusion / vertical / customer IP boundary.

## Architectural significance

The two case studies now exercise materially different physical domains:

```text
HOARE CORE
   │
   ├── Case Study #1: Energy / AesirGrid
   │       └── grid telemetry → predictive maintenance → shadow/control boundary
   │
   └── Case Study #2: Industrial Robotics
           └── robot telemetry → inspection → predictive maintenance → shadow/control boundary
```

The common elements are the platform primitives—not domain-specific implementations.

## Safety boundary

This case study is synthetic. It does not connect to a factory robot, issue motion commands, change safety limits, or claim physical deployment.

Physical control remains downstream of explicit authority and the existing execution boundary.

## Test entry point

```text
backend/tests/test_robotics_case_study.py
```

Focused execution:

```bash
cd backend
pytest tests/test_robotics_case_study.py -v
```
