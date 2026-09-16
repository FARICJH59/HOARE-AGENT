# AesirGrid Case Study — Authorized Control Boundary

**Provenance:** 2026-09-16  
**Case study:** `HOARE-CS-001`

This validation layer connects the existing HOARE product factory, synthetic shadow workflow, authority lease, product authorization boundary, and executor-neutral governance seam.

## Sequence

```text
STAGED PRODUCT
     ↓
SYNTHETIC SHADOW ANALYSIS
     ↓
CONTROLLED ACTION REQUEST
     ↓
VALID AUTHORITY LEASE
     ↓
AEGIS ADMISSION = ALLOW
     ↓
PRODUCT = AUTHORIZED
     ↓
EXISTING EXECUTOR
```

Without the authority lease, the request is `ESCALATE` and the executor is not invoked.

Tenant, product, and mode mismatches are `DENY` and the executor is not invoked.

Expired or revoked leases are `DENY` and the executor is not invoked.

## Executor invariant

The case study uses a recording fake executor only for verification. It does not implement a physical controller and does not replace HOARE's existing executor. The governance seam controls **whether** the existing executor may be called; it does not become the executor.

## Product authorization invariant

`STAGED → AUTHORIZED` is a separate lifecycle transition. A successful controlled admission is required before that transition. Even after authorization, the product definition remains `product-definition-only` and `can_execute == False`.

## Safety boundary

This case study does not connect to a live electrical grid, issue a real setpoint, or claim production operational readiness. It validates the software authorization boundary using deterministic test fixtures.

The next physical-system validation layer remains separately governed and should require deployment-specific evidence, leases, safety constraints, telemetry freshness, rollback behavior, and explicit operational authority.
