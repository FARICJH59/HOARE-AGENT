"""Provider-neutral LLM source for governed engineering tool calls.

Provenance: 2026-09-22 UTC

This module reuses the existing HOARE LLM provider boundary. It only asks the
configured model for a structured engineering tool-call payload; it does not
authorize or execute the requested action.
"""
from __future__ import annotations

import json
from typing import Any

from hoare_engine.agent import _try_openai_call


_ENGINEERING_TOOL_SYSTEM_PROMPT = """You are an engineering tool-planning assistant.

Return exactly one JSON object with exactly these keys:
{
  "tool_name": "<tool name>",
  "arguments": { "<argument>": "<value>" }
}

The response is a request only. Do not claim that the action was executed.
Do not include credentials, authorization tokens, shell interpolation, or
markdown. The receiving control plane validates the tool and arguments and
performs all authorization and execution checks.
"""


class OpenAICompatibleEngineeringToolSource:
    """Adapt the existing HOARE OpenAI-compatible provider into a tool source."""

    def generate_tool_call(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("engineering_prompt_required")
        messages = [
            {"role": "system", "content": _ENGINEERING_TOOL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt.strip()},
        ]
        return _try_openai_call(messages)

    @staticmethod
    def validate_response(raw: str) -> dict[str, Any]:
        """Validate shape only; authorization remains outside this module."""
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("llm_tool_response_required")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("llm_tool_response_invalid_json") from exc
        if not isinstance(payload, dict) or set(payload) != {"tool_name", "arguments"}:
            raise ValueError("llm_tool_response_schema_invalid")
        if not isinstance(payload["tool_name"], str) or not payload["tool_name"].strip():
            raise ValueError("llm_tool_name_required")
        if not isinstance(payload["arguments"], dict):
            raise ValueError("llm_tool_arguments_must_be_object")
        return payload
