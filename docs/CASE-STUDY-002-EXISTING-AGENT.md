# HOARE Case Study #2 — Governing an Existing AI Agent

**Provenance:** 2026-09-16  
**Case study ID:** `HOARE-CS-002`  
**Existing system:** `FARICJH59/SHELF-SCOUTER`  
**Existing model:** Gemma 4 multimodal vision model  
**Purpose:** Validate HOARE around an already-built AI system, not by generating that system from an IR.

## Correct validation question

The test is **not**:

> Can HOARE generate SHELF-SCOUTER?

The test is:

> Can HOARE take an existing developer-built AI system and place governance, admission, evidence, authorization, audit, and execution boundaries around it without replacing the existing AI/vision implementation?

SHELF-SCOUTER already has a Gemma 4 multimodal vision layer, REST endpoints, product detection, OCR, quantity estimation, shelf-position analysis, and structured function-calling output. fileciteturn841file0

It also already contains a HOARE admission boundary for its existing pick execution path, including trusted evidence and server-side resource decisions. fileciteturn842file0 fileciteturn842file7

## Existing-system boundary

```text
                    EXISTING SYSTEM
              SHELF-SCOUTER / GEMMA 4
                         │
                         │ observation / proposed action
                         ▼
                  ┌──────────────┐
                  │     HOARE     │
                  │  admission   │
                  │  governance  │
                  └──────┬───────┘
                         │
                 AEGIS decision
                ┌────────┼────────┐
                ▼        ▼        ▼
              DENY    ESCALATE   ALLOW
                         │          │
                         │          ▼
                         │   EXISTING EXECUTOR
                         │
                         ▼
                  Human authority
```

HOARE does **not** become the model.  
HOARE does **not** regenerate the vision system.  
HOARE does **not** replace the developer's executor.  
HOARE governs whether a proposed consequential action is admissible.

## What HOARE receives

An existing agent can present:

- tenant identity
- agent identity
- project/repository identity
- model/provider identity
- requested action
- target resource
- evidence references
- confidence/verification result
- requested execution mode
- authority/lease information

The existing agent remains responsible for its own model reasoning.

## What HOARE controls

HOARE/AEGIS controls the deterministic boundary around consequential actions:

1. identity
2. tenant scope
3. resource scope
4. action type
5. evidence sufficiency
6. policy compliance
7. risk/mode
8. authority/lease
9. audit evidence
10. final ALLOW / DENY / ESCALATE decision

## Existing LLM example

The model is deliberately treated as an **external existing model**, not as something created by HOARE.

For this case study the existing model is Gemma 4, already used by SHELF-SCOUTER. Its multimodal inference remains outside the HOARE product factory. fileciteturn841file0

The same boundary is intended to work with other existing developers' systems and LLMs through an adapter contract:

```text
Claude / GPT / Gemini / Gemma / local model / existing agent
                         │
                         ▼
                 Existing Agent Adapter
                         │
                         ▼
                       HOARE
                         │
                        AEGIS
                         │
               existing tool/executor
```

## Case-study scenario

An already-deployed SHELF-SCOUTER instance observes a product and proposes a consequential picking operation.

The existing application produces the observation and proposed action.

HOARE then verifies/adjudicates the execution boundary.

### Allowed path

```text
Existing Gemma inference
        ↓
Existing SHELF-SCOUTER logic
        ↓
Trusted product evidence
        ↓
HOARE admission
        ↓
AEGIS = ALLOW
        ↓
Existing executor
        ↓
Execution feedback
        ↓
Audit evidence
```

### Denied path

```text
Existing agent
   ↓
proposed action
   ↓
invalid / untrusted evidence
   ↓
AEGIS = DENY
   ↓
NO EXECUTION
```

### Escalation path

```text
Existing agent
   ↓
valid proposal
   ↓
consequential/high-risk action
   ↓
AEGIS = ESCALATE
   ↓
explicit human authority
   ↓
new admission decision
```

## Why this is the more important HOARE test

A platform that can only govern applications it generates is a factory.

A platform that can govern **applications, agents, models, and developer systems that already exist** is a control plane.

That distinction is central to HOARE's intended architecture.

## Validation criterion

HOARE Case Study #2 succeeds when an existing AI system can remain intact while HOARE provides the deterministic governance boundary around consequential actions.

No IR-generated replacement project is required.

No model retraining is required.

No replacement executor is required.

The existing system remains the system being governed.
