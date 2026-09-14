# HOARE Case Study #1 — Explicit Authority Boundary

**Provenance:** 2026-09-14  
**Case study:** `HOARE-CS-001`  
**Vertical:** AesirGrid predictive maintenance

## Boundary being proven

The product factory can create and verify a product definition, and the shadow workflow can analyze synthetic telemetry. Neither operation grants authority to perform consequential physical control.

The next boundary is explicit authorization:

```text
STAGED PRODUCT
     ↓
CONTROLLED ACTION REQUEST
     ↓
AUTHORITY LEASE
     ↓
AEGIS ADMISSION
  ├── DENY
  ├── ESCALATE
  └── ALLOW
        ↓
STAGED → AUTHORIZED
        ↓
existing executor boundary
```

## Lease requirements

A controlled admission requires:

- tenant identity match
- product identity match
- requested mode match
- valid lease status
- current time within the lease interval
- non-empty action

Expired or revoked leases are denied. Missing authority escalates rather than silently granting permission.

## Execution separation

`AUTHORIZED` is a lifecycle state, not proof that the product definition itself can execute. `ProductDefinition.can_execute` remains false and its authority remains `product-definition-only`.

This preserves the architectural separation:

```text
HOARE governance
      ↓
authorization decision
      ↓
existing execution subsystem
      ↓
physical adapter/controller
```

The case-study authority module does not send grid commands and does not replace the existing executor.

## Validation cases

The focused tests cover:

1. missing lease → `ESCALATE`
2. valid controlled lease → `ALLOW`
3. expired lease → `DENY`
4. revoked lease → `DENY`
5. tenant mismatch → `DENY`
6. product mismatch → `DENY`
7. mode mismatch → `DENY`
8. simulation attempting controlled admission → `DENY`
9. staged product without authority → cannot become `AUTHORIZED`
10. valid authority → `STAGED → AUTHORIZED`
11. authorization does not grant product execution authority

## Enterprise significance

This demonstrates a core HOARE principle:

> **Generation is not authorization. Authorization is not execution.**

That distinction is essential when HOARE is used to manufacture products across energy, industrial, aerospace, defense-industrial, robotics, healthcare, logistics, and scientific domains.
