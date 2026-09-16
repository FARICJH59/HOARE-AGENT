# HOARE Case Study #1 — Evidence and Audit Boundary

**Provenance:** 2026-09-16  
**Case study:** `HOARE-CS-001`  
**Vertical:** AesirGrid predictive maintenance

## Purpose

The case study now includes an explicit evidence artifact between governance and consequential execution. The artifact is designed to prove what HOARE knew and what authority was presented without storing credentials or raw customer telemetry.

## Evidence chain

```text
Telemetry
   ↓
Telemetry Digest
   ↓
Predictive Assessment
   ↓
Model Verification
   ↓
AEGIS Decision
   ↓
Authority Lease (when required)
   ↓
Evidence Bundle
   ↓
Governed Execution Seam
```

## Evidence properties

Each bundle records:

- case-study identifier;
- product identifier;
- tenant identifier;
- execution mode;
- AEGIS decision;
- normalized evidence requirements;
- telemetry digest;
- authority lease identifier when applicable;
- deterministic event digest.

It deliberately does **not** record GitHub tokens, cloud credentials, secrets, or raw customer telemetry.

## Why this matters

This separates three concepts that must not be conflated:

1. **Observation** — what the system received.
2. **Decision evidence** — why a governed action was admitted, denied, or escalated.
3. **Execution** — what an existing executor actually did.

The evidence artifact does not grant authority. A valid lease and AEGIS admission remain prerequisites for controlled execution.

## Current case-study boundary

```text
INTENT
 → PRODUCT FACTORY
 → VERIFIED
 → STAGED
 → SYNTHETIC TELEMETRY
 → SHADOW ANALYSIS
 → EVIDENCE BUNDLE
 → CONTROLLED REQUEST
 → AUTHORITY LEASE
 → AEGIS ADMISSION
 → AUTHORIZED
 → EXISTING EXECUTOR SEAM
```

No physical grid endpoint is contacted by this case study.

## Focused validation

The repository should validate the evidence bundle for deterministic hashing, governance-decision binding, and absence of raw credential fields before this layer is used by a provider-backed deployment.
