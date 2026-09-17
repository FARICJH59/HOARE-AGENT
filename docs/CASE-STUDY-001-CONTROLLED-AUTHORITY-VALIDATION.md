# HOARE Case Study #1 — Evidence-Bound Authority Validation

**Provenance:** 2026-09-16  
**Case study:** `HOARE-CS-001`  
**Boundary:** `STAGED → AUTHORIZED`

This validation adds evidence-carrying authority metadata to the AesirGrid controlled-operation boundary.

A valid lease must identify the authority source, supporting evidence, exact action scope, and audit correlation in addition to tenant, product, mode, validity interval, and status.

The focused tests cover:

- valid evidence-bound admission;
- missing evidence;
- missing authority source;
- missing scope;
- missing audit correlation;
- action mismatch;
- action outside scope;
- wrong tenant;
- wrong product;
- wrong mode;
- expired and revoked leases; and
- prevention of authorization when admission is not `ALLOW`.

The product remains `product-definition-only` and `can_execute == False`. The existing executor remains outside this validation boundary.

No physical grid command or live grid connection is introduced.
