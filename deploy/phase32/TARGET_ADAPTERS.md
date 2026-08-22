# Phase 32 — Target Adapter Framework

Phase 32 establishes a provider-neutral target adapter boundary above the Phase 31 Termux execution worker.

## Initial adapters

- `termux-local`: local inspection/build/test worker; not a production deployment target.
- `vercel-prod`: production deployment boundary; external authenticated provider execution required.
- `customer-vite`: customer-managed Vite build/deployment boundary.

## Lifecycle

```text
prompt → intent → plan → select adapter → inspect → build → test → verify → authorize → deploy → health check → audit
```

## Rules

1. Adapters do not bypass HOARE identity, tenant policy, authorization, verification, or audit controls.
2. Termux may execute local build/test work but is not treated as a production control plane.
3. Production provider credentials remain external to source and must come from an approved secret mechanism.
4. Deployment adapters must support dry-run planning before production execution.
5. No adapter may perform force-push or destructive repository cleanup by default.
6. Build/test and deployment are separate capabilities so HOARE can build locally and deploy elsewhere.
7. New providers implement `TargetAdapter` rather than changing the orchestration core.
