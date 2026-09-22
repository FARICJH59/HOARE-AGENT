"""LLM source for governed Engineering Agent tool calls.

Provenance: 2026-09-22 UTC

This module reuses the existing HOARE LLM provider configuration. It does not
create a second model, executor, or authorization path. Its only output is a
strict structured tool-call payload for the provider-neutral HOARE-CORE
Engineering Agent bridge.
"""

from __future__ import annotations

import json

from hoare_engine.agent import _LLM_MODEL, _try_openai_call

_ENGINEERING_TOOL_SYSTEM_PROMPT = """\\
You are the engineering-tool mode of the existing HOARE Agent.

Return exactly one JSON object:
{
  "tool_name": "<capability name>",
  "arguments": {<structured arguments>}
}

Rules:
1. Choose only a tool capability explicitly named by the user/application.
2. Arguments are data only; never include credentials, authorization decisions,
   shell syntax, or claims that an action has already executed.
3. For test execution, use a structured command array such as ["pytest", "-q"].
4. Do not return markdown, explanations, or additional keys.
5. The downstream Engineering Agent and AEGIS policy decide whether execution
   is permitted.
"""


class EngineeringToolCallSource:
    """Provider adapter that uses the existing HOARE LLM boundary."""

    def __init__(self, *, use_mock_llm: bool = False) -> None:
        self._use_mock_llm = use_mock_llm

    def generate_tool_call(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("engineering_prompt_required")
        messages = [
            {"role": "system", "content": _ENGINEERING_TOOL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        if self._use_mock_llm:
            return json.dumps(
                {
                    "tool_name": "run_tests",
                    "arguments": {
                        "repository": "example/repo",
                        "command": ["pytest", "-q"],
                        "reason": "verify engineering change",
                    },
                }
            )
        return _try_openai_call(messages)

    @staticmethod
    def model_name() -> str:
        """Expose the configured model identity for provenance/telemetry."""
        return _LLM_MODEL
