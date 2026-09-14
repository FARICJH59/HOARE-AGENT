# HOARE Case Study #1 — AesirGrid Predictive Maintenance

**Provenance:** 2026-09-14  
**Case study ID:** `HOARE-CS-001`  
**Platform owner:** Tech Fusion AI ML LLC  
**Vertical:** AesirGrid / energy

## Current proven boundary

```text
INTENT
  ↓
PRODUCT DEFINITION
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
  EXISTING EXECUTOR
```

The executor seam is intentionally **executor-neutral**. HOARE does not become the physical grid controller and does not replace the existing executor.

## Controlled admission invariants

A controlled action cannot invoke the executor unless all of these are true:

- a lease exists;
- lease status is `VALID`;
- current time is inside the lease interval;
- tenant matches;
- product matches;
- requested mode matches the lease mode;
- the action is non-empty.

Missing authority produces `ESCALATE`. Invalid, expired, revoked, or mismatched authority produces `DENY`. Only valid authority produces `ALLOW` and permits the caller-supplied executor to run.

## Test entry points

```text
backend/tests/test_case_study_aesirgrid.py
backend/tests/test_aesirgrid_simulation.py
backend/tests/test_aesirgrid_authority.py
backend/tests/test_aesirgrid_executor.py
```

Focused command:

```bash
cd backend
pytest tests/test_case_study_aesirgrid.py tests/test_aesirgrid_simulation.py tests/test_aesirgrid_authority.py tests/test_aesirgrid_executor.py -v
```

## Validation status

The implementation has been committed to the existing PR branch. GitHub workflow/status execution still needs to validate the focused suite; no CI pass is claimed until that evidence exists.
