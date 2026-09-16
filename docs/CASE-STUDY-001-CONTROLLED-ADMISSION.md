# HOARE Case Study #1 — Controlled Admission Evidence

**Provenance:** 2026-09-16
**Case study:** `HOARE-CS-001`

## Boundary demonstrated

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
AUTHORIZED PRODUCT STATE
        ↓
INJECTED EXISTING EXECUTOR
```

The test harness intentionally injects the existing executor as a callable. The authority module does not implement a physical controller and does not replace the executor.

## Positive path

A staged AesirGrid predictive-maintenance product receives a controlled action request containing:

- tenant identity
- product identity
- requested mode
- action
- current time
- valid authority lease

The lease must match tenant, product, and mode and must be valid at the request time. A valid admission produces `ALLOW`; the staged product may then cross `STAGED → AUTHORIZED`; the existing executor is invoked exactly once by the harness.

## Negative paths

The harness proves that:

- missing authority → `ESCALATE` and zero executor calls;
- wrong tenant → `DENY` and zero executor calls;
- expired lease → `DENY` and zero executor calls;
- revoked lease → `DENY`;
- wrong product → `DENY`;
- wrong mode → `DENY`;
- simulation cannot use the controlled admission boundary;
- a non-`ALLOW` admission cannot authorize the product.

## Security invariant

`ALLOW` is not a general execution permission. It is a decision for the exact request presented at the admission boundary. The product definition itself remains `product-definition-only` and `can_execute == False`.

## Validation status

The code and tests have been added to the case-study branch. CI/local execution must establish the test result; no passing result is claimed by this document until a test runner records it.
