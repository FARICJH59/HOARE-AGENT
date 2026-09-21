"""LLM source for governed Engineering Agent tool calls.

This module reuses the existing HOARE LLM configuration. It does not execute
tools, authorize actions, or import the HOARE-CORE execution layer.
"""

from __future__ import annotations

import json
import os
from typing import Mapping

from .agent import _call_llm


def _mock_engineering_tool_call() -> str:
    return json.dumps({
        "tool_name": "run_tests",
        "arguments": {
            "repository": "example/repo",
            "command": ["pytest", "-q"],
            "reason": "verify the requested engineering change",
        },
    })

_TOOL_SYSTEM_PROMPT = """
You are the reasoning component of the HOARE Engineering Agent.

Return exactly one JSON object:
{
  "tool_name": "<one available tool name>",
  "arguments": {
    "repository": "<repository identifier>",
    "path": "<optional path>",
    "branch": "<optional branch>",
    "content": "<optional file content>",
    "command": ["<program>", "<arg>", "..."],
    "reason": "<why this request is needed>"
  }
}

Rules:
- Select only from the supplied available tools.
- Arguments are structured data, never credentials or authorization.
- Never invent authorization, leases, policy decisions, or execution receipts.
- For commands, use an argv-style JSON array; never return a shell command string.
- Return no markdown and no explanatory text outside the JSON object.
"""


class EngineeringToolLLMSource:
    """Generate structured engineering tool calls using the existing HOARE LLM."""

    def __init__(self, *, use_mock: bool = False) -> None:
        self._use_mock = use_mock

    def generate_tool_call(
        self,
        prompt: str,
        *,
        capabilities: Mapping[str, str] | None = None,
    ) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("engineering_tool_prompt_required")

        available = capabilities or {
            "observe_file": "Request a repository file read.",
            "write_file": "Request a repository file mutation.",
            "run_tests": "Request an explicit test command.",
        }
        capability_text = json.dumps(dict(available), sort_keys=True)
        messages = [
            {"role": "system", "content": _TOOL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Available tools:\n{capability_text}\n\n"
                    f"Engineering task:\n{prompt}"
                ),
            },
        ]
        if self._use_mock:
            return _mock_engineering_tool_call()
        return _call_llm(messages, use_mock=False)


def default_engineering_tool_source() -> EngineeringToolLLMSource:
    """Construct the source using the same existing HOARE LLM configuration."""
    return EngineeringToolLLMSource(
        use_mock=os.getenv("HOARE_ENGINEERING_TOOL_USE_MOCK", "0") == "1"
    )
