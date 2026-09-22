# HOARE Agent — Engineering Tool Bridge

**Development timestamp:** 2026-09-22 UTC  
**Repository:** FARICJH59/HOARE-AGENT  
**Branch:** phase-engineering-agent-llm-bridge

## Purpose

This phase connects the existing HOARE Agent LLM boundary to a provider-neutral engineering tool-call loop without introducing a second LLM, a second execution engine, or direct shell/GitHub authority.

The existing HoareAgent remains the self-verifying data-engineering agent. EngineeringToolLoop is an additive LLM transport boundary for engineering tasks.

## Boundary

```
Existing HOARE LLM configuration
          |
          v
EngineeringToolLoop
          |
          | structured ToolCall
          v
caller-supplied governed handler
          |
          v
HOARE-CORE ToolDispatcher
          |
          v
ActionRequest -> EngineeringPlanner -> AEGIS -> Adapter
          |
          v
ToolResult
          |
          v
EngineeringToolLoop -> same LLM
```

The bridge never decides whether an action is authorized. The handler owns that decision.

## Guarantees

- Reuses HOARE_LLM_BASE_URL, HOARE_LLM_MODEL, and HOARE_LLM_API_KEY.
- Does not create another model or provider configuration.
- Tool arguments remain structured data.
- Malformed tool calls are rejected before the handler is invoked.
- Tool-call identity is preserved.
- Tool results are returned to the model as structured tool messages.
- The loop has a bounded round count.
- The bridge contains no GitHub credentials and no shell execution.
- Existing HoareAgent generate/verify behavior is unchanged.

## Integration contract

The production caller supplies tool schemas and a handler. In the HOARE architecture, that handler is the governed HOARE-CORE dispatcher or a transport adapter that reaches it.

Fusion Search remains an evidence source and is not an execution authority.

## Deliberate non-goals

- replace HoareAgent;
- implement a new LLM;
- bypass AEGIS;
- directly execute Termux commands;
- directly call GitHub;
- automatically merge pull requests;
- grant authority because the LLM requested a tool.