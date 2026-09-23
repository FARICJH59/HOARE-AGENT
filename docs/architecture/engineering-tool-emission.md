# HOARE Engineering Tool Emission

**Development date:** 2026-09-23 UTC  
**Repository:** FARICJH59/HOARE-AGENT  
**Branch:** phase-engineering-tool-emission

## Purpose

This phase connects the existing HOARE LLM provider boundary to the
provider-neutral engineering tool-call contract used by HOARE-CORE.

```
Existing HOARE LLM provider
        |
        v
HoareEngineeringToolSource
        |
        | strict JSON tool proposal
        v
HOARE-CORE LLMToolBridge
        |
        v
ToolDispatcher -> ActionProposal -> AEGIS -> Execution
```

The source **does not execute tools and does not authorize actions**.

## Fusion Search compatibility

Evidence can be supplied to `build_engineering_prompt()` as context for the
LLM's reasoning. The source has no Fusion Search dependency. Fusion Search
therefore remains an evidence provider rather than becoming part of the
execution or authority boundary.

## Existing HOARE Agent compatibility

The existing `HoareAgent.run_task()` generate -> Z3 verify -> self-heal
contract is unchanged. This engineering tool mode reuses the same LLM provider
boundary but does not replace the existing formally verified transformation
workflow.

HOARE-CORE remains responsible for validating the tool-call payload,
observation-backed planning, AEGIS authorization, execution, receipts, and
post-execution verification.
