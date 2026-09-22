# Engineering Tool Source Boundary

**Development date:** 2026-09-22 UTC  
**Repository:** FARICJH59/HOARE-AGENT  
**Branch:** phase-engineering-tool-source

## Purpose

This phase connects the existing HOARE-AGENT LLM provider boundary to the
provider-neutral engineering tool-call contract without replacing the existing
Hoare/Z3 agent.

The new source:

1. reuses the existing OpenAI-compatible LLM configuration;
2. requests one structured engineering tool call;
3. returns the model response as data;
4. performs strict shape validation only.

It does **not** authorize, execute, select an executor, or grant credentials.

## Runtime boundary

```text
Existing HOARE LLM provider
        |
        | structured tool-call JSON
        v
OpenAICompatibleEngineeringToolSource
        |
        | raw validated-shape payload
        v
HOARE-CORE LLMToolBridge
        |
        v
ToolCall -> ToolDispatcher -> ActionProposal -> AEGIS -> Execution
```

The existing `HoareAgent` remains responsible for its established
generate -> Z3 verify -> repair loop. This source does not alter that contract
and does not introduce another model/provider.

## Safety

The model cannot authorize itself.

A response such as a request to write `main` in GitHub still crosses the
HOARE-CORE dispatcher and AEGIS policy. Credentials remain outside the model
and outside this source.

Malformed JSON or malformed tool-call structure is rejected before the
governed dispatcher is reached.

## Verification

The branch includes focused tests for:

- reuse of the existing provider boundary;
- strict tool-call response shape;
- malformed payload rejection;
- absence of authorization/execution state in model output.

The branch also adds a dedicated GitHub Actions workflow for the backend test
suite.
