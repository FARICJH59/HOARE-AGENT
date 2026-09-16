# HOARE Case Study #1 — Validation Record

**Provenance:** 2026-09-16
**Case study:** `HOARE-CS-001`

## Implemented boundary

`SHADOW → CONTROLLED REQUEST → exact AuthorityLease → AEGIS admission → existing executor seam`

The controlled admission is bound to tenant, product, action, mode, and lease validity. Missing authority escalates; mismatches, expired/revoked leases, and invalid requests deny. Only an ALLOW admission delegates to an injected executor.

## Safety boundary

The execution boundary is executor-neutral. It does not implement a physical grid controller, production deployment, or autonomous live authority. A product definition remains `product-definition-only` and does not itself gain execution authority merely by reaching `AUTHORIZED`.

## Required validation

The focused tests must be executed in CI or locally before a passing result is recorded. This document intentionally does not assert an unobserved test result.
