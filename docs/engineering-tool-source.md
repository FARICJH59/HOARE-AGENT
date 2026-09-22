# HOARE Engineering Agent — LLM Tool Source

Date: 2026-09-21 UTC

This seam makes the existing HOARE Agent LLM explicitly capable of producing
the structured ToolCall payload consumed by the governed Engineering Agent.

The boundary is:

LLM -> structured ToolCall -> HOARE-CORE dispatcher -> ActionRequest -> AEGIS -> executor.

The source reuses the existing HOARE_LLM_BASE_URL, HOARE_LLM_MODEL, and
HOARE_LLM_API_KEY configuration through the existing LLM call path. It does
not create a second LLM and does not execute tools.

The LLM only proposes structured data. HOARE-CORE remains responsible for
schema validation, observation-backed planning, AEGIS authorization,
execution, receipts, and verification.

Mock mode is deterministic for CI. Production use supplies an
OpenAI-compatible endpoint through the existing HOARE LLM configuration.

This module is deliberately protocol-compatible with the LLMToolCallSource
contract in HOARE-CORE without importing HOARE-CORE, preserving repository
and IP boundaries.
