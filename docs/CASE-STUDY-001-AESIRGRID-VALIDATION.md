# HOARE Case Study #1 — Validation Boundary

**Provenance:** 2026-09-16

The AesirGrid case study covers the control-plane path from product intent through synthetic shadow analysis, explicit authority leasing, product authorization, and the executor-neutral admission seam.

```text
INTENT
→ PRODUCT FACTORY
→ VERIFIED
→ STAGED
→ SHADOW ANALYSIS
→ CONTROLLED REQUEST
→ AUTHORITY LEASE
→ AEGIS ADMISSION
→ AUTHORIZED
→ EXISTING EXECUTOR SEAM
```

The case study intentionally stops before real physical grid control. The executor remains an injected mechanism and is not replaced by the case-study implementation.

The focused CI workflow is `.github/workflows/hoare-aesirgrid-case-study.yml` and runs the case-study, simulation, authority, control-boundary, end-to-end, and governed-execution tests.
