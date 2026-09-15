# HOARE Case Study #1 — Controlled Authority Validation

**Provenance:** 2026-09-14  
**Case study:** `HOARE-CS-001`  
**Vertical:** AesirGrid

## Boundary being validated

The case study now crosses the boundary between a staged product definition and an authorized controlled operation.

```text
STAGED PRODUCT
      ↓
CONTROLLED ACTION REQUEST
      ↓
AUTHORITY LEASE
      ↓
AEGIS ADMISSION
   ┌──┴──────────┐
   ↓             ↓
 DENY         ESCALATE
                 │
          explicit authority
                 │
                 ↓
               ALLOW
                 ↓
          AUTHORIZED PRODUCT
                 ↓
        existing executor boundary
```

## Invariants

- A staged product cannot directly become `DEPLOYED`.
- No lease produces `ESCALATE`, not implicit authorization.
- Tenant mismatch produces `DENY`.
- Product mismatch produces `DENY`.
- Mode mismatch produces `DENY`.
- Expired or revoked leases produce `DENY`.
- A valid controlled lease produces `ALLOW` and permits only the lifecycle transition `STAGED → AUTHORIZED`.
- Product authorization does **not** make the product itself executable; `can_execute` remains false.
- The existing executor remains responsible for actual execution.
- This case study contains no physical grid command and no live grid connection.

## Why this matters

This demonstrates the key HOARE principle:

> **Generation and staging are not authority. Authority must be explicit, scoped, time-bounded, and governed.**

The same pattern can be reused by other HOARE verticals without creating another control-plane architecture.
