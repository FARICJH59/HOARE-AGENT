# HOARE Case Study #1 — Controlled Admission Boundary

**Provenance:** 2026-09-14

This document records the validation boundary after synthetic shadow analysis.

## Boundary

```text
SHADOW
  ↓
CONTROLLED REQUEST
  ↓
AUTHORITY LEASE
  ↓
AEGIS ADMISSION
  ├── DENY
  ├── ESCALATE
  └── ALLOW
        ↓
INJECTED EXISTING EXECUTOR
```

The case-study code does **not** implement a new physical executor. The canonical `governed_execution` seam accepts an executor through dependency injection and guarantees that it cannot be called until the authority boundary returns `ALLOW`.

## Lease requirements

A controlled request must match:

- tenant identity
- product identity
- requested mode
- current lease time window
- lease status
- non-empty requested action

A missing lease produces `ESCALATE`, while a mismatched, expired, or revoked lease produces `DENY`.

## Architectural separation

```text
HOARE = authority / governance / evidence
Executor = mechanism
```

HOARE does not become the machine controller merely because it governs the controller.

## Safety boundary

`SIMULATION` and `SHADOW` remain non-physical analysis modes. `CONTROLLED` and `LIVE` require explicit authority. The case study still does not issue a real grid command.

## Canonical implementation

```text
backend/hoare_engine/governed_execution.py
backend/tests/test_governed_execution.py
```

Focused command:

```bash
cd backend
pytest tests/test_case_study_aesirgrid.py tests/test_aesirgrid_simulation.py tests/test_aesirgrid_authority.py tests/test_governed_execution.py tests/test_aesirgrid_case_study_end_to_end.py -v
```

## Validation status

GitHub currently has no workflow run attached to the latest case-study head, so no CI pass is claimed yet. The repository's README documents the same local backend test pattern (`pip install -r requirements.txt pytest` followed by `pytest`).
