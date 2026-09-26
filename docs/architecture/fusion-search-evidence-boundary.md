# Fusion Search Evidence Boundary

**Provenance:** 2026-09-26 UTC  
**Repository:** FARICJH59/HOARE-AGENT  
**Phase:** 8 — Fusion Search evidence contract

## Purpose

This phase establishes the clean interface through which Fusion Search can supply
research evidence to the LLM-powered HOARE Agent.

The boundary is provider-neutral. Fusion Search is an evidence provider, not an
authorization or execution component.

## Flow

```
User objective
    |
    v
HOARE Agent / LLM
    |
    | EvidenceQuery
    v
EvidenceProvider
    |
    v
Fusion Search (adapter/provider implementation)
    |
    v
EvidenceBundle
    |
    v
LLM reasoning / planning
    |
    v
ToolCall
    |
    v
HOARE-CORE Engineering Agent
    |
    v
AEGIS -> execution
```

## Security boundary

- Evidence queries are read-only request data.
- Evidence records are immutable and attributable.
- Content hash and retrieval timestamp preserve evidence identity/provenance.
- Evidence is untrusted input to reasoning.
- Evidence never grants permission to mutate files, run commands, commit, push,
  create PRs, or execute consequential actions.
- Authorization remains outside this repository and is enforced by HOARE-CORE/AEGIS.

## Deliberate exclusions

This phase does not call Fusion Search over HTTP, add provider credentials,
modify the existing LLM loop, add a second LLM, add a dispatcher, or authorize execution.

## Next seam

A small Fusion Search adapter can implement EvidenceProvider.search() and map
Fusion Search research/evidence responses into these immutable records without
changing the LLM or HOARE-CORE governance boundary.
