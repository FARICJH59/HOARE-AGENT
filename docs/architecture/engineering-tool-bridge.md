# LLM to Engineering Agent Bridge

**Date:** 2026-09-21 UTC  
**Repository:** FARICJH59/HOARE-AGENT  
**Branch:** phase-engineering-tool-bridge

## Purpose

This is the integration seam between the existing LLM-powered HoareAgent and
the governed Engineering Agent contract in HOARE-CORE.

The bridge does not add another LLM and does not execute anything. It validates
an execution-neutral JSON tool-call envelope and passes it to an explicitly
injected dispatcher.

## Boundary

    existing HOARE LLM
          |
          | structured tool-call JSON
          v
    LLMToolCall / parser
          |
          | injected dispatcher
          v
    HOARE-CORE ToolDispatcher
          |
          v
    ActionProposal -> AEGIS -> execution

The LLM is the reasoning/generation component. HOARE-CORE remains the governed
execution boundary.

## Safety properties

- No shell execution.
- No credentials.
- No authorization state in the LLM envelope.
- No AEGIS decision is created by this module.
- No local filesystem or GitHub operation is performed.
- Dispatcher authority must be supplied explicitly by the caller.
- Existing HoareAgent generation and Hoare/Z3 verification behavior is not
  modified by this change.

## Integration rule

The next integration step may adapt LLMToolCall into the canonical HOARE-CORE
ToolCall type at the application boundary. It must not duplicate AEGIS policy,
leases, receipts, or execution adapters inside HOARE-AGENT.
