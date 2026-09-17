# HOARE Case Study #1 — Explicit Authority Boundary

**Provenance:** 2026-09-16  
**Case study:** `HOARE-CS-001`  
**Vertical:** AesirGrid predictive maintenance

## Boundary being proven

The product factory creates and verifies a product definition, and the shadow workflow analyzes synthetic telemetry. Neither operation grants authority to perform consequential physical control.

The controlled boundary is explicit authorization:

```text
STAGED PRODUCT
     ↓
CONTROLLED ACTION REQUEST
     ↓
AUTHORITY LEASE
     ↓
Exact tenant/product/action/mode/scope checks
     ↓
Validity + evidence + audit checks
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

A controlled admission requires a lease bound to:

- tenant identity
- product identity
- exact requested action
- requested execution mode
- authority source
- evidence references
- action scope
- audit correlation ID
- issuance time
- expiration time
- lease status

Expired or revoked leases are denied. Missing authority escalates rather than silently granting permission.

## Execution separation

`AUTHORIZED` is a lifecycle state, not proof that the product definition itself can execute. `ProductDefinition.can_execute` remains false and its authority remains `product-definition-only`. fileciteturn840file0

The authority module is an admission wrapper that delegates only after successful admission. It does not issue physical commands and does not replace the existing executor. fileciteturn842file0

The focused tests explicitly verify that denied or escalated admissions never call the injected executor. fileciteturn843file0

## Validation cases

The focused tests cover:

1. missing lease → `ESCALATE`
2. valid controlled lease → `ALLOW`
3. expired lease → `DENY`
4. revoked lease → `DENY`
5. tenant mismatch → `DENY`
6. product mismatch → `DENY`
7. mode mismatch → `DENY`
8. exact action mismatch → `DENY`
9. action outside lease scope → `DENY`
10. missing authority source → `DENY`
11. missing authority evidence → `DENY`
12. missing authority scope → `DENY`
13. missing audit correlation → `DENY`
14. simulation attempting controlled admission → `DENY`
15. staged product without authority → cannot become `AUTHORIZED`
16. valid authority → `STAGED → AUTHORIZED`
17. authorization does not grant product execution authority
18. valid admission delegates to the injected existing executor
19. missing/expired authority prevents executor invocation

## Enterprise significance

This demonstrates a core HOARE principle:

> **Generation is not authorization. Authorization is not execution.**

That distinction is essential when HOARE is used to manufacture products across energy, industrial, aerospace, defense-industrial, robotics, healthcare, logistics, and scientific domains.

## Validation status

The implementation has been committed to the case-study branch. CI execution for the latest head must still be observed before claiming the focused suite passes.
