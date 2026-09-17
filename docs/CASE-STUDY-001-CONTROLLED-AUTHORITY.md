# HOARE Case Study #1 — Controlled Authority Validation

**Provenance:** 2026-09-16  
**Case study:** `HOARE-CS-001`  
**Vertical:** AesirGrid

## Boundary being validated

The case study crosses the boundary between a staged product definition and an authorized controlled operation.

```text
STAGED PRODUCT
      ↓
CONTROLLED ACTION REQUEST
      ↓
AUTHORITY LEASE
      ↓
TENANT + PRODUCT + ACTION + MODE + TIME + STATUS
      ↓
AUTHORITY SOURCE + EVIDENCE + SCOPE + AUDIT CORRELATION
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

## Evidence-carrying authority

A lease is not merely a boolean permission. A valid controlled/live lease carries:

- `authority_source` — source of the authority decision;
- `evidence_refs` — evidence supporting admission;
- `scope` — exact action scope;
- `audit_correlation_id` — correlation identifier for audit evidence;
- tenant and product identity;
- exact action identity;
- requested execution mode;
- issuance and expiration times; and
- revocation/validity status.

Admission fails closed when any required authority metadata is absent or when the requested action is outside the lease scope.

## Invariants

- A staged product cannot directly become `DEPLOYED`.
- No lease produces `ESCALATE`, not implicit authorization.
- Tenant mismatch produces `DENY`.
- Product mismatch produces `DENY`.
- Action mismatch produces `DENY`.
- Mode mismatch produces `DENY`.
- Expired or revoked leases produce `DENY`.
- Missing authority source, evidence, scope, or audit correlation produces `DENY`.
- A valid controlled lease produces `ALLOW` and permits only `STAGED → AUTHORIZED`.
- Product authorization does **not** make the product itself executable; `can_execute` remains false.
- The existing executor remains responsible for actual execution.
- An injected executor is invoked only after `ALLOW` admission.
- `DENY` and `ESCALATE` prevent executor invocation.
- This case study contains no physical grid command and no live grid connection.

## Why this matters

This demonstrates a central HOARE principle:

> **Generation and staging are not authority. Authority must be explicit, scoped, time-bounded, evidence-carrying, auditable, and governed.**

The same pattern can be reused by other HOARE verticals without creating another control-plane architecture.

## Test entry points

```text
backend/tests/test_aesirgrid_authority.py
backend/tests/test_case_study_aesirgrid_controlled_e2e.py
```

Run locally:

```bash
cd backend
pytest tests/test_aesirgrid_authority.py tests/test_case_study_aesirgrid_controlled_e2e.py -v
```
