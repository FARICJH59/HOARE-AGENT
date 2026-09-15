# HOARE Case Study #1 — AesirGrid Predictive Maintenance

**Provenance:** 2026-09-14 15:04 EDT  
**Case study ID:** `HOARE-CS-001`  
**Platform owner:** Tech Fusion AI ML LLC  
**Vertical:** AesirGrid / energy

## Current validation path

```text
INTENT
  ↓
PRODUCT FACTORY
  ↓
PLANNED → BUILDING → TESTING → VERIFIED → STAGED
  ↓
SYNTHETIC TELEMETRY
  ↓
PREDICTIVE-MAINTENANCE ASSESSMENT
  ↓
EVIDENCE + FRESHNESS CHECKS
  ↓
AEGIS SHADOW DECISION
  ↓
SHADOW ALLOW
  ↓
CONTROLLED REQUEST
  ↓
EXPLICIT AUTHORITY LEASE
  ↓
AEGIS ADMISSION
  ├── DENY
  ├── ESCALATE
  └── ALLOW
         ↓
STAGED → AUTHORIZED
         ↓
EXISTING EXECUTOR SEAM
```

The canonical executor seam is `hoare_engine.governed_execution`. HOARE governs admission but does not become the physical grid controller and does not replace the existing executor.

## Controlled admission invariants

A controlled action cannot invoke the caller-supplied executor when a product definition is supplied unless all of these are true:

- a lease exists;
- lease status is `VALID`;
- current time is inside the lease interval;
- tenant matches;
- product matches;
- requested mode matches the lease mode;
- the action is non-empty;
- the product has crossed `STAGED → AUTHORIZED` through the explicit authority boundary.

Missing authority produces `ESCALATE`. Invalid, expired, revoked, or mismatched authority produces `DENY`. A valid lease alone is insufficient for an execution-bound product that is still `STAGED`.

## End-to-end case-study validation

The focused end-to-end test connects the layers in one scenario:

```text
enterprise intent
  → proprietary product definition
  → VERIFIED/STAGED lifecycle
  → synthetic telemetry
  → predictive-maintenance assessment
  → SHADOW ALLOW
  → CONTROLLED request without lease → ESCALATE
  → valid lease → AEGIS ALLOW
  → STAGED product → execution DENY
  → explicit STAGED → AUTHORIZED transition
  → existing executor seam → ALLOW / invoked
```

The executor is represented by an injected callback in the test. No physical grid command is emitted.

## IP boundary

The case study keeps vertical IP and customer IP separate:

- Vertical IP: `aesirgrid:grid-models:v1`
- Customer IP: `customer:grid-operator:telemetry:v1`

## Test entry points

```text
backend/tests/test_case_study_aesirgrid.py
backend/tests/test_aesirgrid_simulation.py
backend/tests/test_aesirgrid_authority.py
backend/tests/test_governed_execution.py
backend/tests/test_aesirgrid_case_study_end_to_end.py
```

Focused command:

```bash
cd backend
pytest tests/test_case_study_aesirgrid.py tests/test_aesirgrid_simulation.py tests/test_aesirgrid_authority.py tests/test_governed_execution.py tests/test_aesirgrid_case_study_end_to_end.py -v
```

## Validation status

The implementation is committed to the existing PR branch. The latest implementation commit is `fcbe3a7f7ec278960db716a21cc85549beb8f6b3`.

CI execution is still required before declaring the focused suite passed. No test pass is claimed merely because the implementation and test files are committed.

## Safety boundary

No real grid, cloud provider, or physical control endpoint is contacted by this case study. Controlled/live execution remains subject to explicit authority and the existing executor boundary.
