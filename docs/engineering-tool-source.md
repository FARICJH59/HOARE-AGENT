# HOARE Agent -> Engineering Agent LLM Source

**Development timestamp:** 2026-09-22 UTC  
**Repository:** FARICJH59/HOARE-AGENT  
**Branch:** phase-engineering-tool-output

## Purpose

This adds the missing provider-side source for the existing Engineering Agent
tool bridge. It does not add a second LLM.

```text
Existing HOARE LLM configuration
            |
            v
EngineeringToolCallSource
            |
            | strict JSON tool call
            v
HOARE-CORE LLMToolBridge
            |
            v
ToolDispatcher
            |
            v
ActionRequest -> AEGIS -> Execution
```

## No-conflict invariant

The existing HoareAgent.run_task() and its Hoare/Z3 verification loop are
unchanged. Formal transformation generation remains available for tasks that
use that contract.

Engineering tool generation is a separate output mode of the same configured
LLM/provider boundary. It only emits structured data. It does not execute
tools, grant authority, hold credentials, or bypass AEGIS.

The downstream HOARE-CORE bridge remains responsible for parsing the payload,
correlating the call, observation-backed planning, AEGIS admission, execution,
and result verification.

## Mock behavior

CI can use use_mock_llm=True to produce a deterministic run_tests payload.
This exercises the provider-side contract without requiring a live model.

A live deployment uses the existing OpenAI-compatible endpoint and configured
model; no second model is introduced.