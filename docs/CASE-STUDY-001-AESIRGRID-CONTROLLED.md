# HOARE Case Study #1 — Controlled Admission Boundary

**Provenance:** 2026-09-12

This document records the next validation boundary after synthetic shadow analysis.

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

The important property is that the case-study code does **not** implement a new physical executor. It accepts an executor through dependency injection and guarantees that the executor cannot be called until the authority boundary returns `ALLOW`.

## Lease requirements

A controlled request must match:

- tenant identity
- product identity
- requested mode
- current lease time window
- lease status
- non-empty requested action

A missing lease produces `ESCALATE`, while a mismatched, expired, or revoked lease produces `DENY`.

## Why this matters

This establishes the architectural separation:

```text
HOARE = authority / governance / evidence
Executor = mechanism
```

HOARE does not become the machine controller merely because it governs the controller.

## Safety boundary

`SIMULATION` and `SHADOW` remain non-physical analysis modes. `CONTROLLED` and `LIVE` require explicit authority. The case study still does not issue a real grid command.

## Test entry point

```text
backend/tests/test_aesirgrid_authority.py
backend/tests/test_aesirgrid_control_boundary.py
```

Focused command:

```bash
cd backend
pytest tests/test_aesirgrid_authority.py tests/test_aesirgrid_control_boundary.py -v
```
