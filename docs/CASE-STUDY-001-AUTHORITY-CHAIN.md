# HOARE Case Study #1 — Authority Chain

**Provenance:** 2026-09-16

```text
STAGED
  ↓
CONTROLLED REQUEST
  ↓
EXACT LEASE
  ↓
EVIDENCE + SCOPE + AUDIT CORRELATION
  ↓
AEGIS ADMISSION
  ↓
ALLOW
  ↓
AUTHORIZED
```

The authority lease is bound to tenant, product, exact action, mode, validity interval, authority source, evidence references, scope, and audit correlation. Missing or mismatched authority metadata fails closed. Authorization remains distinct from execution; the existing executor is not replaced and no physical grid command is introduced.
